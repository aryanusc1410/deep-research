"""
LangGraph workflow implementation for the research agent.

This module implements the core research workflow using LangGraph's stateful
orchestration. The workflow has three main phases:
1. Planning - Generate search queries based on the research question
2. Searching - Execute searches and gather sources
3. Synthesizing - Generate final report from gathered information

The workflow supports both single-provider and dual-search modes, with
automatic provider fallback and comprehensive error handling.
"""

import sys
from typing import Any
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

from constants import (
    DEFAULT_GEMINI_MODEL,
    DEFAULT_TEMPERATURE,
    PROVIDER_GEMINI,
    PROVIDER_OPENAI,
    DETAILED_QUERY_COUNT_OPENAI,
    DETAILED_QUERY_COUNT_GEMINI,
    SIMPLE_QUERY_COUNT_OPENAI,
    SIMPLE_QUERY_COUNT_GEMINI,
    TEMPLATE_DETAILED_REPORT,
    TEMPLATE_TWO_COLUMN,
    SEARCH_TOOL_TAVILY,
    SEARCH_TOOL_SERP,
    GEMINI_MAX_SOURCES_LIMIT,
)
from templates import REPORT_TEMPLATES, add_provider_specific_instructions
from tools import (
    make_tavily_tool,
    make_serp_tool,
    merge_and_rank_results,
    dedupe_keep_best,
    execute_search_queries,
)
from settings import settings
from logger import logger, log
from exceptions import LLMTimeoutError


# ============================================================================
# State Management
# ============================================================================

def initial_state(
    query: str,
    config: dict[str, Any],
    messages: list[dict[str, Any]]
) -> dict[str, Any]:
    """
    Create the initial state for a research workflow.

    Args:
        query: The research question to investigate
        config: Configuration dictionary with provider, model, template, etc.
        messages: Previous conversation messages for context

    Returns:
        Initial state dictionary with all required fields
    """
    return {
        "query": query,
        "config": config,
        "messages": messages,
        "plan": "",
        "search_results": [],
        "sources": [],
        "report": None,
        "tavily_report": None,
        "serp_report": None,
    }


# ============================================================================
# LLM Factory and Invocation
# ============================================================================

def get_llm(provider: str, model: str | None):
    """
    Create an LLM instance with appropriate configuration.

    This function handles provider-specific configuration and includes
    automatic fallback to OpenAI if Gemini is unavailable.

    Args:
        provider: Provider name ('openai' or 'gemini')
        model: Optional specific model ID to use

    Returns:
        Configured LLM instance (ChatOpenAI or ChatGoogleGenerativeAI)

    Note:
        The actual provider used may differ from requested due to fallback logic
    """
    log(f"[LLM] Requested provider={provider}, model={model}")

    # Get actual available provider with fallback
    actual_provider = settings.get_available_provider(provider)

    if actual_provider != provider:
        log(f"[LLM] ⚠️  Provider changed: {provider} → {actual_provider}")

    if actual_provider == PROVIDER_GEMINI:
        return ChatGoogleGenerativeAI(
            model=model or DEFAULT_GEMINI_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=DEFAULT_TEMPERATURE,
            max_output_tokens=settings.GEMINI_MAX_OUTPUT_TOKENS,
            max_retries=settings.GEMINI_MAX_RETRIES,
            timeout=settings.GEMINI_TIMEOUT_SECONDS,
            request_timeout=settings.GEMINI_REQUEST_TIMEOUT,
        )

    return ChatOpenAI(
        model=model or settings.MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=DEFAULT_TEMPERATURE
    )


def invoke_llm_safe(
    llm,
    messages: list[dict[str, str]],
    is_gemini: bool = False,
    timeout_seconds: int | None = None
):
    """
    Invoke LLM with timeout protection for Gemini.

    OpenAI calls run normally without timeout restrictions, while Gemini
    calls are wrapped in a timeout to prevent hanging requests due to
    quota limits or API issues.

    Args:
        llm: The LLM instance to invoke
        messages: List of message dictionaries with 'role' and 'content'
        is_gemini: Whether this is a Gemini provider (enables timeout)
        timeout_seconds: Optional custom timeout in seconds

    Returns:
        LLM response object

    Raises:
        LLMTimeoutError: If Gemini request exceeds timeout
        Exception: Any other LLM invocation errors
    """
    # OpenAI runs normally without timeout wrapper
    if not is_gemini:
        return llm.invoke(messages)

    # Gemini gets timeout protection
    if timeout_seconds is None:
        timeout_seconds = settings.GEMINI_TIMEOUT_SECONDS

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(llm.invoke, messages)
            try:
                result = future.result(timeout=timeout_seconds)
                # Force flush after getting result from thread
                sys.stdout.flush()
                return result
            except FuturesTimeoutError:
                error_msg = f"Gemini request exceeded {timeout_seconds}s timeout"
                log(f"[LLM] {error_msg}", force_flush=True)
                raise LLMTimeoutError(error_msg)
    except LLMTimeoutError:
        raise
    except Exception as e:
        log(f"[LLM] Error during Gemini invocation: {e}", force_flush=True)
        raise


# ============================================================================
# Planning Phase
# ============================================================================

def step_plan(state: dict[str, Any]) -> dict[str, Any]:
    """
    Planning phase: Generate search queries from the research question.

    This phase analyzes the research question and breaks it down into
    specific, targeted search queries that will be used in the search phase.

    Args:
        state: Current workflow state

    Returns:
        Updated state with 'plan' field populated

    Note:
        - Query count is adjusted based on template complexity and provider
        - Gemini uses fewer queries to conserve quota
        - Timeout errors result in a fallback simple plan
    """
    logger.info("Graph", "PLAN - Starting planning phase...", force_flush=True)

    # Get actual provider (with fallback if needed)
    requested_provider = state["config"]["provider"]
    actual_provider = settings.get_available_provider(requested_provider)

    # Update config if provider changed
    if actual_provider != requested_provider:
        state["config"]["provider"] = actual_provider
        logger.info(
            "Graph",
            f"PLAN - Provider updated: {requested_provider} → {actual_provider}",
            force_flush=True
        )

    # Get LLM instance
    llm = get_llm(actual_provider, state["config"].get("model"))

    # Determine query count based on template and provider
    is_detailed = state["config"]["template"] == TEMPLATE_DETAILED_REPORT
    is_gemini = actual_provider == PROVIDER_GEMINI

    if is_gemini:
        query_count = DETAILED_QUERY_COUNT_GEMINI if is_detailed else SIMPLE_QUERY_COUNT_GEMINI
    else:
        query_count = DETAILED_QUERY_COUNT_OPENAI if is_detailed else SIMPLE_QUERY_COUNT_OPENAI

    # Build planning prompt
    system_prompt = (
        f"You are a research planner. Break the user query into {query_count} "
        f"specific web searches. Return numbered queries only. Be concise."
    )

    logger.info("Graph", "PLAN - Invoking LLM...", force_flush=True)

    try:
        response = invoke_llm_safe(
            llm,
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": state["query"]}
            ],
            is_gemini=is_gemini
        )
        state["plan"] = response.content
        logger.info(
            "Graph",
            f"PLAN - Complete. Generated {len(response.content)} chars",
            force_flush=True
        )
    except LLMTimeoutError:
        # Fallback to simple plan if timeout occurs
        logger.warning("Graph", "PLAN - Timeout occurred, using fallback plan", force_flush=True)
        state["plan"] = (
            f"1. {state['query']}\n"
            f"2. {state['query']} overview\n"
            f"3. {state['query']} details"
        )

    return state


# ============================================================================
# Search Phase
# ============================================================================

def step_search(state: dict[str, Any]) -> dict[str, Any]:
    """
    Searching phase: Execute search queries and gather sources.

    This phase can operate in two modes:
    1. Single search (Tavily only) - Default mode
    2. Dual search (Tavily + SerpAPI) - If SerpAPI key is available

    In dual search mode, both tools run in parallel for efficiency.

    Args:
        state: Current workflow state with 'plan' field populated

    Returns:
        Updated state with 'search_results' and 'sources' fields populated

    Raises:
        APIKeyError: If Tavily API key is missing
    """
    logger.info("Graph", "SEARCH - Starting search phase...", force_flush=True)

    # Validate Tavily key exists
    settings.validate_search_requirements()

    # Get actual provider and apply budget limits
    actual_provider = state["config"]["provider"]
    is_gemini = actual_provider == PROVIDER_GEMINI

    max_budget = settings.GEMINI_MAX_SEARCHES if is_gemini else settings.MAX_SEARCHES
    budget = min(int(state["config"]["search_budget"]), max_budget)

    logger.info(
        "Graph",
        f"SEARCH - Using budget of {budget} queries (provider: {actual_provider})",
        force_flush=True
    )

    # Parse queries from plan
    raw_lines = [line for line in state["plan"].split("\n") if line.strip()]
    queries = [q.strip(" -0123456789.\"") for q in raw_lines][:budget]

    # Check if dual search is possible
    use_dual = settings.can_use_dual_search

    if use_dual:
        # Dual search mode: Run both tools in parallel
        all_hits = _execute_dual_search(queries)
    else:
        # Single search mode: Tavily only
        all_hits = _execute_single_search(queries)

    # Update state with results
    state["search_results"] = all_hits
    state["sources"] = _format_sources(all_hits)

    logger.info("Graph", "SEARCH - Complete", force_flush=True)
    return state


def _execute_dual_search(queries: list[str]) -> list[dict[str, Any]]:
    """
    Execute searches using both Tavily and SerpAPI in parallel.

    Args:
        queries: List of search query strings

    Returns:
        Merged and deduplicated list of search results
    """
    logger.info(
        "Graph",
        f"SEARCH - Running DUAL search with {len(queries)} queries...",
        force_flush=True
    )

    # Create both tools
    tavily_tool = make_tavily_tool(settings.TAVILY_API_KEY, max_results=5)
    serp_tool = make_serp_tool(settings.SERP_API_KEY, max_results=5)

    # Run both searches in parallel
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_tavily = executor.submit(
            execute_search_queries, tavily_tool, queries, SEARCH_TOOL_TAVILY
        )
        future_serp = executor.submit(
            execute_search_queries, serp_tool, queries, SEARCH_TOOL_SERP
        )

        tavily_hits = future_tavily.result()
        serp_hits = future_serp.result()

    logger.info("Graph", f"SEARCH - Tavily returned {len(tavily_hits)} results", force_flush=True)
    logger.info("Graph", f"SEARCH - SerpAPI returned {len(serp_hits)} results", force_flush=True)

    # Merge and deduplicate
    merged_results = merge_and_rank_results(tavily_hits, serp_hits)
    logger.info(
        "Graph",
        f"SEARCH - Merged to {len(merged_results)} unique sources",
        force_flush=True
    )

    return merged_results


def _execute_single_search(queries: list[str]) -> list[dict[str, Any]]:
    """
    Execute searches using Tavily only.

    Args:
        queries: List of search query strings

    Returns:
        Deduplicated list of search results
    """
    logger.info(
        "Graph",
        f"SEARCH - Running SINGLE search (Tavily) with {len(queries)} queries...",
        force_flush=True
    )

    tavily_tool = make_tavily_tool(settings.TAVILY_API_KEY, max_results=5)
    all_hits = execute_search_queries(tavily_tool, queries, SEARCH_TOOL_TAVILY)

    # Deduplicate results
    deduped_results = dedupe_keep_best(all_hits)
    logger.info(
        "Graph",
        f"SEARCH - Deduped to {len(deduped_results)} unique sources",
        force_flush=True
    )

    return deduped_results


def _format_sources(search_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Format raw search results into structured source citations.

    Args:
        search_results: Raw search result dictionaries

    Returns:
        List of formatted source dictionaries with id, title, url, etc.
    """
    sources = []
    for i, hit in enumerate(search_results):
        snippet = hit.get("content") or ""
        sources.append({
            "id": i + 1,
            "title": hit.get("title"),
            "url": hit.get("url"),
            "snippet": snippet[:300],  # Limit snippet length
            "query": hit.get("query"),
            "source": hit.get("search_tool", "unknown")
        })
    return sources


# ============================================================================
# Synthesis Phase
# ============================================================================

def step_synthesize(state: dict[str, Any]) -> dict[str, Any]:
    """
    Synthesis phase: Generate final report from gathered sources.

    This phase can operate in two modes:
    1. Single report generation - One report from all sources
    2. Dual report generation - Generate two reports (one per search tool),
       then use LLM to select the better one

    Args:
        state: Current workflow state with 'sources' field populated

    Returns:
        Updated state with 'report' field populated (and optionally
        'tavily_report' and 'serp_report' in dual mode)
    """
    logger.info("Graph", "SYNTHESIZE - Starting synthesis phase...", force_flush=True)

    # Get configuration
    actual_provider = state["config"]["provider"]
    llm = get_llm(actual_provider, state["config"].get("model"))
    template_name = state["config"]["template"]
    query = state["query"]
    sources = state["sources"]
    is_gemini = actual_provider == PROVIDER_GEMINI

    # Check if we have dual search results
    has_tavily = any(s.get("source") == SEARCH_TOOL_TAVILY for s in sources)
    has_serp = any(s.get("source") == SEARCH_TOOL_SERP for s in sources)
    use_dual = settings.can_use_dual_search and has_tavily and has_serp

    if use_dual:
        # Dual synthesis mode
        _execute_dual_synthesis(state, llm, query, sources, template_name, is_gemini)
    else:
        # Single synthesis mode
        _execute_single_synthesis(state, llm, query, sources, template_name, is_gemini)

    logger.info("Graph", "SYNTHESIZE - Complete", force_flush=True)
    return state


def _execute_dual_synthesis(
    state: dict[str, Any],
    llm,
    query: str,
    sources: list[dict[str, Any]],
    template_name: str,
    is_gemini: bool
) -> None:
    """
    Generate two reports (one per search tool) and select the better one.

    Args:
        state: Workflow state to update
        llm: LLM instance
        query: Research query
        sources: All gathered sources
        template_name: Template to use for generation
        is_gemini: Whether using Gemini provider
    """
    logger.info(
        "Graph",
        "SYNTHESIZE - Generating reports from BOTH search sources...",
        force_flush=True
    )

    # Generate two reports in parallel
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_tavily = executor.submit(
            _synthesize_single_report,
            llm, query, sources, template_name, SEARCH_TOOL_TAVILY, is_gemini
        )
        future_serp = executor.submit(
            _synthesize_single_report,
            llm, query, sources, template_name, SEARCH_TOOL_SERP, is_gemini
        )

        try:
            timeout = settings.GEMINI_REQUEST_TIMEOUT if is_gemini else None
            tavily_report = future_tavily.result(timeout=timeout)
            serp_report = future_serp.result(timeout=timeout)
        except FuturesTimeoutError:
            logger.error(
                "Graph",
                "SYNTHESIZE - One or both reports timed out",
                force_flush=True
            )
            tavily_report = "Report timed out"
            serp_report = "Report timed out"

    logger.info(
        "Graph",
        f"SYNTHESIZE - Tavily report: {len(tavily_report) if tavily_report else 0} chars",
        force_flush=True
    )
    logger.info(
        "Graph",
        f"SYNTHESIZE - SerpAPI report: {len(serp_report) if serp_report else 0} chars",
        force_flush=True
    )

    # Ask LLM to choose the better report
    winning_tool, final_report = _select_best_report(
        llm, query, tavily_report, serp_report, is_gemini
    )

    # Filter sources to match winning tool
    filtered_sources = [s for s in sources if s.get("source") == winning_tool]

    # Update state
    state["tavily_report"] = tavily_report
    state["serp_report"] = serp_report
    state["report"] = {
        "structure": template_name,
        "content": final_report,
        "citations": filtered_sources,
        "dual_search": True,
        "winning_tool": winning_tool
    }

    logger.info(
        "Graph",
        f"SYNTHESIZE - Winner: {winning_tool} with {len(final_report)} chars",
        force_flush=True
    )


def _execute_single_synthesis(
    state: dict[str, Any],
    llm,
    query: str,
    sources: list[dict[str, Any]],
    template_name: str,
    is_gemini: bool
) -> None:
    """
    Generate a single report from all available sources.

    Args:
        state: Workflow state to update
        llm: LLM instance
        query: Research query
        sources: All gathered sources
        template_name: Template to use for generation
        is_gemini: Whether using Gemini provider
    """
    logger.info("Graph", "SYNTHESIZE - Generating single report...", force_flush=True)

    # Limit sources for Gemini to conserve quota
    limited_sources = sources
    if is_gemini and len(sources) > GEMINI_MAX_SOURCES_LIMIT:
        logger.info(
            "Graph",
            f"SYNTHESIZE - Limiting sources from {len(sources)} to {GEMINI_MAX_SOURCES_LIMIT} for Gemini",
            force_flush=True
        )
        limited_sources = sources[:GEMINI_MAX_SOURCES_LIMIT]

    # Build sources text
    sources_text = "\n".join([
        f"[{s['id']}] {s['title']} — {s['url']}"
        for s in limited_sources
    ])

    # Get template with provider-specific instructions
    template_text = REPORT_TEMPLATES[template_name]
    template_text = add_provider_specific_instructions(template_text, is_gemini, template_name)

    system_prompt = f"{template_text}\nOnly cite using the numeric indices from SOURCES."
    user_prompt = f"QUERY:\n{query}\n\nSOURCES:\n{sources_text}"

    try:
        response = invoke_llm_safe(
            llm,
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            is_gemini=is_gemini
        )

        state["report"] = {
            "structure": template_name,
            "content": response.content,
            "citations": limited_sources,
            "dual_search": False
        }

        logger.info(
            "Graph",
            f"SYNTHESIZE - Report: {len(response.content)} chars",
            force_flush=True
        )

    except LLMTimeoutError:
        state["report"] = {
            "structure": template_name,
            "content": "Report generation timed out. Please try with fewer search queries or use OpenAI.",
            "citations": limited_sources,
            "dual_search": False
        }


def _synthesize_single_report(
    llm,
    query: str,
    sources: list[dict[str, Any]],
    template_name: str,
    source_filter: str,
    is_gemini: bool
) -> str:
    """
    Generate a single report from filtered sources.

    Args:
        llm: LLM instance
        query: Research query
        sources: All available sources
        template_name: Template to use
        source_filter: Filter sources by this tool name
        is_gemini: Whether using Gemini provider

    Returns:
        Generated report content
    """
    # Filter sources
    filtered_sources = [s for s in sources if s.get("source") == source_filter]

    if not filtered_sources:
        return None

    # Limit sources for Gemini
    if is_gemini and len(filtered_sources) > GEMINI_MAX_SOURCES_LIMIT:
        logger.info(
            "Graph",
            f"SYNTHESIZE - Limiting sources from {len(filtered_sources)} to {GEMINI_MAX_SOURCES_LIMIT} for Gemini",
            force_flush=True
        )
        filtered_sources = filtered_sources[:GEMINI_MAX_SOURCES_LIMIT]

    # Build sources text
    sources_text = "\n".join([
        f"[{s['id']}] {s['title']} — {s['url']} (from {s.get('source', 'unknown')})"
        for s in filtered_sources
    ])

    # Get template with provider-specific instructions
    template_text = REPORT_TEMPLATES[template_name]
    template_text = add_provider_specific_instructions(template_text, is_gemini, template_name)

    system_prompt = f"{template_text}\nOnly cite using the numeric indices from SOURCES."
    user_prompt = f"QUERY:\n{query}\n\nSOURCES:\n{sources_text}"

    try:
        response = invoke_llm_safe(
            llm,
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            is_gemini=is_gemini
        )

        content = response.content

        # Post-process for Gemini two_column template
        if template_name == TEMPLATE_TWO_COLUMN and is_gemini:
            content = _extract_table_from_response(content)

        return content

    except LLMTimeoutError:
        logger.error(
            "Graph",
            "SYNTHESIZE - Timeout occurred during synthesis",
            force_flush=True
        )
        return "Report generation timed out. Please try with fewer search queries or use OpenAI."


def _select_best_report(
    llm,
    query: str,
    tavily_report: str,
    serp_report: str,
    is_gemini: bool
) -> tuple[str, str]:
    """
    Use LLM to compare two reports and select the better one.

    Args:
        llm: LLM instance
        query: Original research query
        tavily_report: Report generated from Tavily sources
        serp_report: Report generated from SerpAPI sources
        is_gemini: Whether using Gemini provider

    Returns:
        Tuple of (winning_tool_name, winning_report_content)
    """
    logger.info(
        "Graph",
        "SYNTHESIZE - Asking LLM to select the BEST report...",
        force_flush=True
    )

    comparison_prompt = f"""You are a research quality evaluator. You have two research reports on the same topic from different search sources.

QUERY: {query}

TAVILY REPORT:
{tavily_report}

---

SERPAPI REPORT:
{serp_report}

---

Your task: Analyze both reports and select the BETTER one. Consider:
- Comprehensiveness and depth of information
- Source quality and credibility
- Factual accuracy and specificity
- Direct relevance to the query
- Clarity and structure

Respond with ONLY ONE of these exact phrases, nothing else:
- "TAVILY" if the Tavily report is better
- "SERPAPI" if the SerpAPI report is better

Your choice:"""

    try:
        choice_response = invoke_llm_safe(
            llm,
            [{"role": "user", "content": comparison_prompt}],
            is_gemini=is_gemini
        )
        choice = choice_response.content.strip().upper()
    except LLMTimeoutError:
        logger.warning(
            "Graph",
            "SYNTHESIZE - Comparison timed out, defaulting to Tavily",
            force_flush=True
        )
        choice = "TAVILY"

    logger.info("Graph", f"SYNTHESIZE - LLM chose: {choice}", force_flush=True)

    # Return winner
    if "SERPAPI" in choice:
        return SEARCH_TOOL_SERP, serp_report
    else:
        return SEARCH_TOOL_TAVILY, tavily_report


def _extract_table_from_response(content: str) -> str:
    """
    Extract markdown table from Gemini response that may include extra text.

    Gemini sometimes adds explanatory text before/after tables. This function
    extracts just the table portion for cleaner output.

    Args:
        content: Full response content from Gemini

    Returns:
        Extracted table content (or original if no table found)
    """
    lines = content.split('\n')
    table_lines = []
    in_table = False

    for line in lines:
        stripped = line.strip()

        # Check if this line is part of a table (contains |)
        if '|' in stripped:
            in_table = True
            table_lines.append(line)
        elif in_table and not stripped:
            # Empty line after table - might be end of table
            continue
        elif in_table and stripped:
            # Non-table line after we were in a table - table ended
            break

    if table_lines:
        result = '\n'.join(table_lines)
        logger.info(
            "Graph",
            f"Extracted table with {len(table_lines)} lines from {len(lines)} total lines",
            force_flush=True
        )
        return result

    # If no table found, return original content
    logger.warning(
        "Graph",
        "WARNING: No table found in response, returning original content",
        force_flush=True
    )
    return content