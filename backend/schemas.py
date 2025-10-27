"""
Pydantic models for request/response validation and serialization.

This module defines all data models used throughout the application,
ensuring type safety and automatic validation of API requests and responses.
"""

from typing import Literal, Any
from pydantic import BaseModel, Field

from constants import (
    TEMPLATE_BULLET_SUMMARY,
    TEMPLATE_TWO_COLUMN,
    TEMPLATE_DETAILED_REPORT,
    PROVIDER_OPENAI,
    PROVIDER_GEMINI,
)


# ============================================================================
# Type Definitions
# ============================================================================

Provider = Literal["openai", "gemini"]
"""Valid LLM provider names."""

TemplateName = Literal["bullet_summary", "two_column", "detailed_report"]
"""Valid report template names."""

MessageRole = Literal["user", "assistant", "tool"]
"""Valid message roles in conversation history."""

StreamEventType = Literal["token", "status", "done", "log", "plan", "sources", "progress", "error"]
"""Valid server-sent event types."""


# ============================================================================
# Request Models
# ============================================================================

class UserMessage(BaseModel):
    """
    Represents a single message in the conversation history.

    Attributes:
        role: The role of the message sender (user, assistant, or tool)
        content: The actual message content
    """

    role: MessageRole = "user"
    content: str

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "role": "user",
                "content": "What are the latest trends in AI?"
            }
        }


class RunConfig(BaseModel):
    """
    Configuration options for a research run.

    Attributes:
        provider: The LLM provider to use (openai or gemini)
        model: Optional specific model ID to use
        template: The report template/format to generate
        search_budget: Number of search queries to execute (1-10)
    """

    provider: Provider = PROVIDER_OPENAI
    model: str | None = None
    template: TemplateName = TEMPLATE_BULLET_SUMMARY
    search_budget: int = Field(default=4, ge=1, le=10)

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "template": "bullet_summary",
                "search_budget": 4
            }
        }


class RunRequest(BaseModel):
    """
    Request model for the /run endpoint.

    Attributes:
        query: The research question/query to investigate
        messages: Previous conversation messages for context
        config: Configuration options for this research run
    """

    query: str = Field(..., min_length=1, description="The research query")
    messages: list[UserMessage] = Field(default_factory=list)
    config: RunConfig = RunConfig()

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "query": "What are the latest breakthroughs in quantum computing?",
                "messages": [],
                "config": {
                    "provider": "openai",
                    "template": "bullet_summary",
                    "search_budget": 4
                }
            }
        }


# ============================================================================
# Response Models
# ============================================================================

class Source(BaseModel):
    """
    Represents a single source/citation in a research report.

    Attributes:
        id: Unique identifier for the source
        title: Title of the source document
        url: URL of the source
        snippet: Short excerpt/preview of the content
        query: The search query that found this source
        source: Which search tool found this source
    """

    id: int
    title: str
    url: str
    snippet: str
    query: str | None = None
    source: str | None = None

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "id": 1,
                "title": "Quantum Computing Breakthrough 2024",
                "url": "https://example.com/quantum-breakthrough",
                "snippet": "Researchers announced a major advancement...",
                "query": "quantum computing breakthroughs 2024",
                "source": "Tavily"
            }
        }


class Report(BaseModel):
    """
    Represents a generated research report.

    Attributes:
        structure: The template used to generate the report
        content: The actual report content (markdown formatted)
        citations: List of sources cited in the report
        dual_search: Whether dual search mode was used
        winning_tool: If dual search, which tool's report was selected
    """

    structure: TemplateName
    content: str
    citations: list[dict[str, Any]]
    dual_search: bool = False
    winning_tool: str | None = None

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "structure": "bullet_summary",
                "content": "## TL;DR\n\n- Key finding 1 [1]\n- Key finding 2 [2]",
                "citations": [
                    {
                        "id": 1,
                        "title": "Source Title",
                        "url": "https://example.com"
                    }
                ],
                "dual_search": True,
                "winning_tool": "Tavily"
            }
        }


class StreamChunk(BaseModel):
    """
    Represents a single chunk in a server-sent event stream.

    Attributes:
        event: The type of event being sent
        data: The event payload data
    """

    event: StreamEventType = "token"
    data: dict[str, Any] = Field(default_factory=dict)

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "event": "status",
                "data": {"phase": "searching"}
            }
        }


# ============================================================================
# Internal State Models
# ============================================================================

class ResearchState(BaseModel):
    """
    Represents the internal state during a research workflow.

    This is used internally by the LangGraph workflow to track
    progress through the planning, searching, and synthesis phases.

    Attributes:
        query: The original research query
        config: Configuration for this research run
        messages: Conversation history
        plan: Generated search plan
        search_results: Raw search results from tools
        sources: Formatted sources for citation
        report: Final generated report
        tavily_report: Report from Tavily search (if dual search)
        serp_report: Report from SerpAPI search (if dual search)
    """

    query: str
    config: dict[str, Any]
    messages: list[dict[str, Any]]
    plan: str = ""
    search_results: list[dict[str, Any]] = Field(default_factory=list)
    sources: list[dict[str, Any]] = Field(default_factory=list)
    report: dict[str, Any] | None = None
    tavily_report: str | None = None
    serp_report: str | None = None

    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True