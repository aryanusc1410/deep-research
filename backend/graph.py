# backend/graph.py
from typing import Dict, Any, List
import asyncio
import sys
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from templates import REPORT_TEMPLATES
from tools import make_tavily_tool, make_serp_tool, merge_and_rank_results, dedupe_keep_best
from settings import settings

def log(msg: str, force_flush: bool = False):
    """
    Helper function to print logs with optional forced flush.
    Force flush is needed when logging from thread pool executors.
    """
    print(msg)
    if force_flush:
        sys.stdout.flush()

def initial_state(query: str, config: Dict[str, Any], messages: list):
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

def get_llm(provider: str, model: str | None):
    """
    Get LLM with appropriate configuration and limits.
    Automatically falls back to OpenAI if Gemini key is missing.
    """
    log(f"[LLM] Requested provider={provider}, model={model}")
    
    # Get actual available provider (with fallback logic)
    actual_provider = settings.get_available_provider(provider)
    
    if actual_provider != provider:
        log(f"[LLM] ⚠️  Provider changed: {provider} → {actual_provider}")
    
    if actual_provider == "gemini":
        return ChatGoogleGenerativeAI(
            model=model or "gemini-2.0-flash-exp",
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.2,
            max_output_tokens=settings.GEMINI_MAX_OUTPUT_TOKENS,
            max_retries=settings.GEMINI_MAX_RETRIES,
            timeout=settings.GEMINI_TIMEOUT_SECONDS,
            request_timeout=settings.GEMINI_REQUEST_TIMEOUT,
        )
    
    return ChatOpenAI(
        model=model or settings.MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=0.2
    )

def invoke_llm_safe(llm, messages, is_gemini: bool = False, timeout_seconds: int = None):
    """
    Invoke LLM with timeout protection ONLY for Gemini.
    OpenAI runs normally without timeout restrictions.
    """
    # If NOT Gemini, just invoke normally without any timeout wrapper
    if not is_gemini:
        return llm.invoke(messages)
    
    # For Gemini, apply timeout protection
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
            except TimeoutError:
                log(f"[LLM] Gemini request timed out after {timeout_seconds}s", force_flush=True)
                raise TimeoutError(f"Gemini request exceeded {timeout_seconds}s timeout")
    except Exception as e:
        log(f"[LLM] Error during Gemini invocation: {e}", force_flush=True)
        raise

def step_plan(state: Dict[str, Any]) -> Dict[str, Any]:
    log("[Graph] PLAN - Starting planning phase...", force_flush=True)
    
    # Get actual provider being used (with fallback)
    requested_provider = state["config"]["provider"]
    actual_provider = settings.get_available_provider(requested_provider)
    
    # Update config if provider changed
    if actual_provider != requested_provider:
        state["config"]["provider"] = actual_provider
        log(f"[Graph] PLAN - Provider updated: {requested_provider} → {actual_provider}", force_flush=True)
    
    llm = get_llm(actual_provider, state["config"].get("model"))
    
    # Adjust query count based on template and ACTUAL provider
    is_detailed = state["config"]["template"] == "detailed_report"
    is_gemini = actual_provider == "gemini"
    
    # Use fewer searches for Gemini to conserve quota
    if is_gemini:
        query_count = "4-6" if is_detailed else "3-4"
    else:
        query_count = "8-12" if is_detailed else "3-6"
    
    system = f"You are a research planner. Break the user query into {query_count} specific web searches. Return numbered queries only. Be concise."
    log("[Graph] PLAN - Invoking LLM...", force_flush=True)
    
    try:
        resp = invoke_llm_safe(llm, [
            {"role":"system","content":system},
            {"role":"user","content":state["query"]}
        ], is_gemini=is_gemini)
        state["plan"] = resp.content
        log(f"[Graph] PLAN - Complete. Generated {len(resp.content)} chars", force_flush=True)
    except TimeoutError as e:
        log(f"[Graph] PLAN - Timeout occurred, using fallback plan", force_flush=True)
        state["plan"] = f"1. {state['query']}\n2. {state['query']} overview\n3. {state['query']} details"
    
    return state

def run_search_with_tool(tool, queries: List[str], tool_name: str) -> List[Dict]:
    """Run searches with a specific tool"""
    all_hits = []
    for idx, q in enumerate(queries, 1):
        log(f"[Graph] {tool_name} - Query {idx}/{len(queries)}: {q}", force_flush=True)
        try:
            hits = tool.run(q) if hasattr(tool, 'run') else tool.func(q)
            if isinstance(hits, list):
                for h in hits:
                    h["query"] = q
                    h["search_tool"] = tool_name
                all_hits.extend(hits)
                log(f"[Graph] {tool_name} - Query {idx} returned {len(hits)} results", force_flush=True)
        except Exception as e:
            log(f"[Graph] {tool_name} - Query {idx} failed: {e}", force_flush=True)
    return all_hits

def step_search(state: Dict[str, Any]) -> Dict[str, Any]:
    log("[Graph] SEARCH - Starting search phase...", force_flush=True)
    
    # Validate that Tavily key exists
    settings.validate_search_requirements()
    
    # Get actual provider (might have been changed during planning)
    actual_provider = state["config"]["provider"]
    
    # Apply stricter budget for Gemini ONLY
    is_gemini = actual_provider == "gemini"
    max_budget = settings.GEMINI_MAX_SEARCHES if is_gemini else settings.MAX_SEARCHES
    
    budget = min(int(state["config"]["search_budget"]), max_budget)
    log(f"[Graph] SEARCH - Using budget of {budget} queries (provider: {actual_provider})", force_flush=True)
    
    # Parse queries from plan
    raw_lines = [l for l in state["plan"].split("\n") if l.strip()]
    queries = [q.strip(" -0123456789.\"") for q in raw_lines][:budget]
    
    # Check if dual search is ACTUALLY possible
    use_dual = settings.can_use_dual_search
    
    if use_dual:
        log(f"[Graph] SEARCH - Running DUAL search with {len(queries)} queries...", force_flush=True)
        tavily_tool = make_tavily_tool(settings.TAVILY_API_KEY, max_results=5)
        serp_tool = make_serp_tool(settings.SERP_API_KEY, max_results=5)
        
        # Run both searches in parallel using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_tavily = executor.submit(run_search_with_tool, tavily_tool, queries, "Tavily")
            future_serp = executor.submit(run_search_with_tool, serp_tool, queries, "SerpAPI")
            
            tavily_hits = future_tavily.result()
            serp_hits = future_serp.result()
        
        log(f"[Graph] SEARCH - Tavily returned {len(tavily_hits)} results", force_flush=True)
        log(f"[Graph] SEARCH - SerpAPI returned {len(serp_hits)} results", force_flush=True)
        
        # Merge and deduplicate results
        all_hits = merge_and_rank_results(tavily_hits, serp_hits)
        log(f"[Graph] SEARCH - Merged to {len(all_hits)} unique sources", force_flush=True)
    else:
        # Fallback to Tavily only
        log(f"[Graph] SEARCH - Running SINGLE search (Tavily) with {len(queries)} queries...", force_flush=True)
        tavily_tool = make_tavily_tool(settings.TAVILY_API_KEY, max_results=5)
        all_hits = run_search_with_tool(tavily_tool, queries, "Tavily")
        all_hits = dedupe_keep_best(all_hits)
        log(f"[Graph] SEARCH - Deduped to {len(all_hits)} unique sources", force_flush=True)
    
    state["search_results"] = all_hits
    state["sources"] = [
        {
            "id": i+1, 
            "title": h.get("title"), 
            "url": h.get("url"), 
            "snippet": (h.get("content") or "")[:300], 
            "query": h.get("query"),
            "source": h.get("search_tool", "unknown")
        }
        for i, h in enumerate(all_hits)
    ]
    log("[Graph] SEARCH - Complete", force_flush=True)
    return state

def extract_table_from_response(content: str) -> str:
    """
    Extract markdown table from Gemini response that might include extra text.
    Returns just the table portion.
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
        log(f"[Graph] Extracted table with {len(table_lines)} lines from {len(lines)} total lines", force_flush=True)
        return result
    
    # If no table found, return original content
    log(f"[Graph] WARNING: No table found in response, returning original content", force_flush=True)
    return content

def synthesize_single_report(
    llm, 
    query: str, 
    sources: List[Dict], 
    template: str,
    source_filter: str = None,
    is_gemini: bool = False
) -> str:
    """Generate a single report from sources"""
    # Filter sources if needed
    filtered_sources = sources
    if source_filter:
        filtered_sources = [s for s in sources if s.get("source") == source_filter]
    
    if not filtered_sources:
        return None
    
    # Limit sources for Gemini ONLY to reduce token usage
    if is_gemini and len(filtered_sources) > 10:
        log(f"[Graph] SYNTHESIZE - Limiting sources from {len(filtered_sources)} to 10 for Gemini", force_flush=True)
        filtered_sources = filtered_sources[:10]
    
    template_text = REPORT_TEMPLATES[template]
    src_text = "\n".join([
        f"[{s['id']}] {s['title']} — {s['url']} (from {s.get('source', 'unknown')})" 
        for s in filtered_sources
    ])
    
    # Special handling for two_column template with Gemini
    if template == "two_column" and is_gemini:
        additional_instruction = (
            "\n\n**CRITICAL INSTRUCTIONS FOR THIS TASK**: "
            "You MUST output ONLY a markdown table, nothing else. "
            "NO introduction, NO explanation, NO conclusion. "
            "Maximum 12 rows. Each cell: 1-2 sentences maximum. "
            "Start directly with: | Claim | Evidence |"
        )
    elif is_gemini:
        additional_instruction = "\nBe concise and focused. Prioritize quality over length."
    else:
        additional_instruction = ""
    
    system = f"{template_text}{additional_instruction}\nOnly cite using the numeric indices from SOURCES."
    user = f"QUERY:\n{query}\n\nSOURCES:\n{src_text}"
    
    try:
        # Use safe invoke that only applies timeout to Gemini
        resp = invoke_llm_safe(llm, [
            {"role":"system","content":system},
            {"role":"user","content":user}
        ], is_gemini=is_gemini)
        
        content = resp.content
        
        # Post-process for Gemini two_column: extract only the table if there's extra text
        if template == "two_column" and is_gemini:
            content = extract_table_from_response(content)
            log(f"[Graph] Final table content length: {len(content)} chars", force_flush=True)
        
        return content
    except TimeoutError:
        log("[Graph] SYNTHESIZE - Gemini timeout occurred during synthesis", force_flush=True)
        return f"Report generation timed out. Please try with fewer search queries or use OpenAI instead of Gemini."

def step_synthesize(state: Dict[str, Any]) -> Dict[str, Any]:
    log("[Graph] SYNTHESIZE - Starting synthesis phase...", force_flush=True)
    
    # Get actual provider being used
    actual_provider = state["config"]["provider"]
    
    llm = get_llm(actual_provider, state["config"].get("model"))
    template = state["config"]["template"]
    query = state["query"]
    sources = state["sources"]
    is_gemini = actual_provider == "gemini"
    
    # Check if we have dual search results
    has_tavily = any(s.get("source") == "Tavily" for s in sources)
    has_serp = any(s.get("source") == "SerpAPI" for s in sources)
    use_dual = settings.can_use_dual_search and has_tavily and has_serp
    
    if use_dual:
        log("[Graph] SYNTHESIZE - Generating reports from BOTH search sources...", force_flush=True)
        
        # Generate two reports in parallel
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_tavily = executor.submit(
                synthesize_single_report, llm, query, sources, template, "Tavily", is_gemini
            )
            future_serp = executor.submit(
                synthesize_single_report, llm, query, sources, template, "SerpAPI", is_gemini
            )
            
            try:
                # Only apply timeout to Gemini
                timeout = settings.GEMINI_REQUEST_TIMEOUT if is_gemini else None
                tavily_report = future_tavily.result(timeout=timeout)
                serp_report = future_serp.result(timeout=timeout)
            except TimeoutError:
                log("[Graph] SYNTHESIZE - One or both reports timed out", force_flush=True)
                tavily_report = "Report timed out"
                serp_report = "Report timed out"
        
        log(f"[Graph] SYNTHESIZE - Tavily report: {len(tavily_report) if tavily_report else 0} chars", force_flush=True)
        log(f"[Graph] SYNTHESIZE - SerpAPI report: {len(serp_report) if serp_report else 0} chars", force_flush=True)
        
        # Ask LLM to choose the BETTER report (with timeout protection only for Gemini)
        log("[Graph] SYNTHESIZE - Asking LLM to select the BEST report...", force_flush=True)
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
            choice_resp = invoke_llm_safe(llm, [{"role":"user","content":comparison_prompt}], is_gemini=is_gemini)
            choice = choice_resp.content.strip().upper()
        except TimeoutError:
            log("[Graph] SYNTHESIZE - Comparison timed out, defaulting to Tavily", force_flush=True)
            choice = "TAVILY"
        
        log(f"[Graph] SYNTHESIZE - LLM chose: {choice}", force_flush=True)
        
        # Select the winner
        if "SERPAPI" in choice:
            final_report = serp_report
            winning_tool = "SerpAPI"
            # Filter sources to only show SerpAPI sources
            filtered_sources = [s for s in sources if s.get("source") == "SerpAPI"]
        else:  # Default to Tavily if unclear
            final_report = tavily_report
            winning_tool = "Tavily"
            # Filter sources to only show Tavily sources
            filtered_sources = [s for s in sources if s.get("source") == "Tavily"]
        
        state["tavily_report"] = tavily_report
        state["serp_report"] = serp_report
        state["report"] = {
            "structure": template,
            "content": final_report,
            "citations": filtered_sources,
            "dual_search": True,
            "winning_tool": winning_tool
        }
        log(f"[Graph] SYNTHESIZE - Winner: {winning_tool} with {len(final_report)} chars", force_flush=True)
    else:
        # Single source synthesis
        log("[Graph] SYNTHESIZE - Generating single report...", force_flush=True)
        
        # Limit sources for Gemini ONLY
        limited_sources = sources
        if is_gemini and len(sources) > 10:
            log(f"[Graph] SYNTHESIZE - Limiting sources from {len(sources)} to 10 for Gemini", force_flush=True)
            limited_sources = sources[:10]
        
        src_text = "\n".join([f"[{s['id']}] {s['title']} — {s['url']}" for s in limited_sources])
        template_text = REPORT_TEMPLATES[template]
        
        # Add conciseness instruction for Gemini ONLY
        additional_instruction = "\nBe concise and focused. Prioritize quality over length." if is_gemini else ""
        system = f"{template_text}{additional_instruction}\nOnly cite using the numeric indices from SOURCES."
        user = f"QUERY:\n{query}\n\nSOURCES:\n{src_text}"
        
        try:
            # Use safe invoke that only applies timeout to Gemini
            resp = invoke_llm_safe(llm, [
                {"role":"system","content":system},
                {"role":"user","content":user}
            ], is_gemini=is_gemini)
            state["report"] = {
                "structure": template,
                "content": resp.content,
                "citations": limited_sources,
                "dual_search": False
            }
            log(f"[Graph] SYNTHESIZE - Report: {len(resp.content)} chars", force_flush=True)
        except TimeoutError:
            state["report"] = {
                "structure": template,
                "content": "Report generation timed out. Please try with fewer search queries or use OpenAI instead of Gemini.",
                "citations": limited_sources,
                "dual_search": False
            }
    
    log("[Graph] SYNTHESIZE - Complete", force_flush=True)
    return state