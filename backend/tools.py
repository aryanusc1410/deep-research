"""
Search tool implementations and result processing utilities.

This module provides wrappers for different search APIs (Tavily and SerpAPI)
and utilities for merging, deduplicating, and ranking search results.
"""

from typing import Any, Callable

from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.utilities import SerpAPIWrapper
from langchain.tools import Tool

from constants import (
    DEFAULT_SEARCH_RESULTS,
    MAX_SEARCH_RESULTS,
    SEARCH_TOOL_TAVILY,
    SEARCH_TOOL_SERP,
)
from logger import logger


# ============================================================================
# Tool Factory Functions
# ============================================================================

def make_tavily_tool(
    tavily_api_key: str | None,
    max_results: int = DEFAULT_SEARCH_RESULTS
) -> TavilySearchResults:
    """
    Create a Tavily search tool instance.

    Tavily is a search API optimized for LLMs and RAG applications,
    providing high-quality results with built-in content extraction.

    Args:
        tavily_api_key: Tavily API key
        max_results: Maximum number of results to return per query

    Returns:
        Configured TavilySearchResults tool instance

    Example:
        >>> tool = make_tavily_tool("tvly-...", max_results=5)
        >>> results = tool.run("quantum computing")
    """
    return TavilySearchResults(
        max_results=max_results,
        tavily_api_key=tavily_api_key,
        include_answer=True,
        include_raw_content=True
    )


def make_serp_tool(
    serp_api_key: str | None,
    max_results: int = DEFAULT_SEARCH_RESULTS
) -> Tool:
    """
    Create a SerpAPI search tool instance.

    SerpAPI provides Google search results with rich structured data
    including organic results, knowledge graphs, and more.

    Args:
        serp_api_key: SerpAPI key
        max_results: Maximum number of results to return per query

    Returns:
        LangChain Tool wrapping SerpAPI functionality

    Example:
        >>> tool = make_serp_tool("serp-key-...", max_results=5)
        >>> results = tool.func("machine learning")
    """
    search_wrapper = SerpAPIWrapper(serpapi_api_key=serp_api_key)

    def serp_search(query: str) -> list[dict[str, Any]]:
        """
        Execute a search query using SerpAPI and format results.

        Args:
            query: Search query string

        Returns:
            List of formatted search result dictionaries

        Note:
            Errors are logged but don't raise exceptions to ensure
            graceful degradation if one search tool fails.
        """
        try:
            # Execute search
            results = search_wrapper.results(query)

            # Extract and format organic results
            formatted_results: list[dict[str, Any]] = []
            organic_results = results.get("organic_results", [])[:max_results]

            for item in organic_results:
                formatted_results.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "content": item.get("snippet", ""),
                    "source": "serp"
                })

            return formatted_results

        except Exception as e:
            logger.error(SEARCH_TOOL_SERP, f"Search failed for query '{query}': {e}")
            return []

    return Tool(
        name="serp_search",
        description="Search using SerpAPI for current web results",
        func=serp_search
    )


# ============================================================================
# Result Processing Utilities
# ============================================================================

def dedupe_keep_best(
    items: list[dict[str, Any]],
    max_items: int = MAX_SEARCH_RESULTS
) -> list[dict[str, Any]]:
    """
    Deduplicate search results by URL, keeping first occurrence.

    When multiple results point to the same URL (common across different
    search tools), this function keeps only the first one encountered.

    Args:
        items: List of search result dictionaries
        max_items: Maximum number of items to return after deduplication

    Returns:
        Deduplicated list of search results (up to max_items)

    Example:
        >>> results = [
        ...     {"url": "https://a.com", "title": "A"},
        ...     {"url": "https://a.com", "title": "A duplicate"},
        ...     {"url": "https://b.com", "title": "B"}
        ... ]
        >>> dedupe_keep_best(results)
        [{"url": "https://a.com", "title": "A"}, {"url": "https://b.com", "title": "B"}]
    """
    seen_urls: set[str] = set()
    unique_items: list[dict[str, Any]] = []

    for item in items:
        # Get URL from either 'url' or 'source' field
        url = item.get("url") or item.get("source")

        # Skip items without URL or with duplicate URLs
        if not url or url in seen_urls:
            continue

        seen_urls.add(url)
        unique_items.append(item)

    return unique_items[:max_items]


def merge_and_rank_results(
    tavily_results: list[dict[str, Any]],
    serp_results: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """
    Merge results from multiple search tools with diversity optimization.

    This function interleaves results from different search tools to ensure
    diversity in the final result set, then deduplicates by URL.

    The interleaving strategy ensures that if one tool has better results,
    they're evenly distributed rather than clustered.

    Args:
        tavily_results: Search results from Tavily
        serp_results: Search results from SerpAPI

    Returns:
        Merged and deduplicated list of search results

    Example:
        >>> tavily = [{"url": "https://a.com", "source": "tavily"}]
        >>> serp = [{"url": "https://b.com", "source": "serp"}]
        >>> merged = merge_and_rank_results(tavily, serp)
        >>> len(merged) == 2
        True
    """
    merged: list[dict[str, Any]] = []
    max_length = max(len(tavily_results), len(serp_results))

    # Interleave results from both sources
    for i in range(max_length):
        # Add Tavily result if available
        if i < len(tavily_results):
            result = tavily_results[i].copy()
            result["source"] = SEARCH_TOOL_TAVILY
            merged.append(result)

        # Add SerpAPI result if available
        if i < len(serp_results):
            result = serp_results[i].copy()
            result["source"] = SEARCH_TOOL_SERP
            merged.append(result)

    # Deduplicate by URL, keeping first occurrence (respects interleaving)
    return dedupe_keep_best(merged)


# ============================================================================
# Search Execution Helpers
# ============================================================================

def execute_search_queries(
    tool: Any,
    queries: list[str],
    tool_name: str
) -> list[dict[str, Any]]:
    """
    Execute multiple search queries with a single tool.

    This function handles errors gracefully, logging failures but continuing
    with remaining queries to maximize result coverage.

    Args:
        tool: Search tool instance (Tavily or SerpAPI)
        queries: List of search query strings
        tool_name: Name of the tool (for logging)

    Returns:
        Combined list of all search results from all queries

    Note:
        Each result is annotated with the query that generated it
        and the source tool name.
    """
    all_results: list[dict[str, Any]] = []

    for idx, query in enumerate(queries, 1):
        logger.info(tool_name, f"Query {idx}/{len(queries)}: {query}", force_flush=True)

        try:
            # Execute search (handle both tool types)
            if hasattr(tool, 'run'):
                results = tool.run(query)
            else:
                results = tool.func(query)

            # Process results if they're a list
            if isinstance(results, list):
                for result in results:
                    result["query"] = query
                    result["search_tool"] = tool_name

                all_results.extend(results)
                logger.info(
                    tool_name,
                    f"Query {idx} returned {len(results)} results",
                    force_flush=True
                )

        except Exception as e:
            logger.error(tool_name, f"Query {idx} failed: {e}", force_flush=True)
            # Continue with next query despite error

    return all_results