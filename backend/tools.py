from typing import List, Dict
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.utilities import SerpAPIWrapper
from langchain.tools import Tool

def make_tavily_tool(tavily_api_key: str | None, max_results: int = 5):
    """Create Tavily search tool"""
    return TavilySearchResults(
        max_results=max_results,
        tavily_api_key=tavily_api_key,
        include_answer=True,
        include_raw_content=True
    )

def make_serp_tool(serp_api_key: str | None, max_results: int = 5):
    """Create SerpAPI search tool"""
    search = SerpAPIWrapper(serpapi_api_key=serp_api_key)
    
    def serp_search(query: str) -> List[Dict]:
        """Run SerpAPI search and format results"""
        try:
            results = search.results(query)
            formatted = []
            
            # Extract organic results
            organic = results.get("organic_results", [])[:max_results]
            for item in organic:
                formatted.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "content": item.get("snippet", ""),
                    "source": "serp"
                })
            
            return formatted
        except Exception as e:
            print(f"[SerpAPI] Error: {e}")
            return []
    
    return Tool(
        name="serp_search",
        description="Search using SerpAPI for current web results",
        func=serp_search
    )

def dedupe_keep_best(items: List[Dict]) -> List[Dict]:
    """Deduplicate by URL, keeping first occurrence"""
    seen, out = set(), []
    for it in items:
        url = it.get("url") or it.get("source")
        if not url or url in seen: 
            continue
        seen.add(url)
        out.append(it)
    return out[:20]

def merge_and_rank_results(tavily_results: List[Dict], serp_results: List[Dict]) -> List[Dict]:
    """Merge results from both sources, interleaving them for diversity"""
    merged = []
    max_len = max(len(tavily_results), len(serp_results))
    
    for i in range(max_len):
        if i < len(tavily_results):
            tavily_results[i]["source"] = "tavily"
            merged.append(tavily_results[i])
        if i < len(serp_results):
            serp_results[i]["source"] = "serp"
            merged.append(serp_results[i])
    
    return dedupe_keep_best(merged)