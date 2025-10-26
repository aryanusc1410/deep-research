# backend/graph.py
from typing import Dict, Any, List
import asyncio
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from templates import REPORT_TEMPLATES
from tools import make_tavily_tool, make_serp_tool, merge_and_rank_results, dedupe_keep_best
from settings import settings

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
    """Get LLM with appropriate configuration and limits"""
    print(f"[LLM] Loading model from provider={provider}, model={model}")
    
    if provider == "gemini":
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
                return future.result(timeout=timeout_seconds)
            except TimeoutError:
                print(f"[LLM] Gemini request timed out after {timeout_seconds}s")
                raise TimeoutError(f"Gemini request exceeded {timeout_seconds}s timeout")
    except Exception as e:
        print(f"[LLM] Error during Gemini invocation: {e}")
        raise

def step_plan(state: Dict[str, Any]) -> Dict[str, Any]:
    print("[Graph] PLAN - Starting planning phase...")
    llm = get_llm(state["config"]["provider"], state["config"].get("model"))
    
    # Adjust query count based on template and provider
    is_detailed = state["config"]["template"] == "detailed_report"
    is_gemini = state["config"]["provider"] == "gemini"
    
    # Use fewer searches for Gemini to conserve quota
    if is_gemini:
        query_count = "4-6" if is_detailed else "3-4"
    else:
        query_count = "8-12" if is_detailed else "3-6"
    
    system = f"You are a research planner. Break the user query into {query_count} specific web searches. Return numbered queries only. Be concise."
    print("[Graph] PLAN - Invoking LLM...")
    
    try:
        resp = invoke_llm_safe(llm, [
            {"role":"system","content":system},
            {"role":"user","content":state["query"]}
        ], is_gemini=is_gemini)
        state["plan"] = resp.content
        print(f"[Graph] PLAN - Complete. Generated {len(resp.content)} chars")
    except TimeoutError as e:
        print(f"[Graph] PLAN - Timeout occurred, using fallback plan")
        state["plan"] = f"1. {state['query']}\n2. {state['query']} overview\n3. {state['query']} details"
    
    return state

def run_search_with_tool(tool, queries: List[str], tool_name: str) -> List[Dict]:
    """Run searches with a specific tool"""
    all_hits = []
    for idx, q in enumerate(queries, 1):
        print(f"[Graph] {tool_name} - Query {idx}/{len(queries)}: {q}")
        try:
            hits = tool.run(q) if hasattr(tool, 'run') else tool.func(q)
            if isinstance(hits, list):
                for h in hits:
                    h["query"] = q
                    h["search_tool"] = tool_name
                all_hits.extend(hits)
                print(f"[Graph] {tool_name} - Query {idx} returned {len(hits)} results")
        except Exception as e:
            print(f"[Graph] {tool_name} - Query {idx} failed: {e}")
    return all_hits

def step_search(state: Dict[str, Any]) -> Dict[str, Any]:
    print("[Graph] SEARCH - Starting search phase...")
    
    # Apply stricter budget for Gemini ONLY
    is_gemini = state["config"]["provider"] == "gemini"
    max_budget = settings.GEMINI_MAX_SEARCHES if is_gemini else settings.MAX_SEARCHES
    
    budget = min(int(state["config"]["search_budget"]), max_budget)
    print(f"[Graph] SEARCH - Using budget of {budget} queries (provider: {state['config']['provider']})")
    
    # Parse queries from plan
    raw_lines = [l for l in state["plan"].split("\n") if l.strip()]
    queries = [q.strip(" -0123456789.\"") for q in raw_lines][:budget]
    
    # Check if dual search is enabled
    use_dual = settings.USE_DUAL_SEARCH and settings.SERP_API_KEY and settings.TAVILY_API_KEY
    
    if use_dual:
        print(f"[Graph] SEARCH - Running DUAL search with {len(queries)} queries...")
        tavily_tool = make_tavily_tool(settings.TAVILY_API_KEY, max_results=5)
        serp_tool = make_serp_tool(settings.SERP_API_KEY, max_results=5)
        
        # Run both searches in parallel using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_tavily = executor.submit(run_search_with_tool, tavily_tool, queries, "Tavily")
            future_serp = executor.submit(run_search_with_tool, serp_tool, queries, "SerpAPI")
            
            tavily_hits = future_tavily.result()
            serp_hits = future_serp.result()
        
        print(f"[Graph] SEARCH - Tavily returned {len(tavily_hits)} results")
        print(f"[Graph] SEARCH - SerpAPI returned {len(serp_hits)} results")
        
        # Merge and deduplicate results
        all_hits = merge_and_rank_results(tavily_hits, serp_hits)
        print(f"[Graph] SEARCH - Merged to {len(all_hits)} unique sources")
    else:
        # Fallback to Tavily only
        print(f"[Graph] SEARCH - Running SINGLE search (Tavily) with {len(queries)} queries...")
        tavily_tool = make_tavily_tool(settings.TAVILY_API_KEY, max_results=5)
        all_hits = run_search_with_tool(tavily_tool, queries, "Tavily")
        all_hits = dedupe_keep_best(all_hits)
        print(f"[Graph] SEARCH - Deduped to {len(all_hits)} unique sources")
    
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
    print("[Graph] SEARCH - Complete")
    return state

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
        print(f"[Graph] SYNTHESIZE - Limiting sources from {len(filtered_sources)} to 10 for Gemini")
        filtered_sources = filtered_sources[:10]
    
    template_text = REPORT_TEMPLATES[template]
    src_text = "\n".join([
        f"[{s['id']}] {s['title']} — {s['url']} (from {s.get('source', 'unknown')})" 
        for s in filtered_sources
    ])
    
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
        return resp.content
    except TimeoutError:
        print("[Graph] SYNTHESIZE - Gemini timeout occurred during synthesis")
        return f"Report generation timed out. Please try with fewer search queries or use OpenAI instead of Gemini."

def step_synthesize(state: Dict[str, Any]) -> Dict[str, Any]:
    print("[Graph] SYNTHESIZE - Starting synthesis phase...")
    llm = get_llm(state["config"]["provider"], state["config"].get("model"))
    template = state["config"]["template"]
    query = state["query"]
    sources = state["sources"]
    is_gemini = state["config"]["provider"] == "gemini"
    
    # Check if we have dual search results
    has_tavily = any(s.get("source") == "Tavily" for s in sources)
    has_serp = any(s.get("source") == "SerpAPI" for s in sources)
    use_dual = settings.USE_DUAL_SEARCH and has_tavily and has_serp
    
    if use_dual:
        print("[Graph] SYNTHESIZE - Generating reports from BOTH search sources...")
        
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
                print("[Graph] SYNTHESIZE - One or both reports timed out")
                tavily_report = "Report timed out"
                serp_report = "Report timed out"
        
        print(f"[Graph] SYNTHESIZE - Tavily report: {len(tavily_report) if tavily_report else 0} chars")
        print(f"[Graph] SYNTHESIZE - SerpAPI report: {len(serp_report) if serp_report else 0} chars")
        
        # Ask LLM to choose the BETTER report (with timeout protection only for Gemini)
        print("[Graph] SYNTHESIZE - Asking LLM to select the BEST report...")
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
            print("[Graph] SYNTHESIZE - Comparison timed out, defaulting to Tavily")
            choice = "TAVILY"
        
        print(f"[Graph] SYNTHESIZE - LLM chose: {choice}")
        
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
        print(f"[Graph] SYNTHESIZE - Winner: {winning_tool} with {len(final_report)} chars")
    else:
        # Single source synthesis
        print("[Graph] SYNTHESIZE - Generating single report...")
        
        # Limit sources for Gemini ONLY
        limited_sources = sources
        if is_gemini and len(sources) > 10:
            print(f"[Graph] SYNTHESIZE - Limiting sources from {len(sources)} to 10 for Gemini")
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
            print(f"[Graph] SYNTHESIZE - Report: {len(resp.content)} chars")
        except TimeoutError:
            state["report"] = {
                "structure": template,
                "content": "Report generation timed out. Please try with fewer search queries or use OpenAI instead of Gemini.",
                "citations": limited_sources,
                "dual_search": False
            }
    
    print("[Graph] SYNTHESIZE - Complete")
    return state