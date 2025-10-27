"""
Custom exception classes for the Deep Research Agent application.

This module defines all custom exceptions used throughout the application,
providing clear and specific error handling for different scenarios.
"""


class DeepResearchError(Exception):
    """Base exception class for all Deep Research Agent errors."""

    def __init__(self, message: str, details: dict | None = None):
        """
        Initialize the base exception.

        Args:
            message: Human-readable error message
            details: Optional dictionary with additional error context
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigurationError(DeepResearchError):
    """Raised when there's a configuration or settings issue."""

    pass


class APIKeyError(ConfigurationError):
    """Raised when required API keys are missing or invalid."""

    pass


class ProviderError(DeepResearchError):
    """Raised when there's an issue with an LLM provider."""

    pass


class ProviderUnavailableError(ProviderError):
    """Raised when a requested provider is not available."""

    pass


class SearchError(DeepResearchError):
    """Raised when there's an issue with search operations."""

    pass


class SearchToolError(SearchError):
    """Raised when a search tool fails."""

    pass


class LLMTimeoutError(ProviderError):
    """Raised when an LLM request times out."""

    pass


class SynthesisError(DeepResearchError):
    """Raised when report synthesis fails."""

    pass


class ValidationError(DeepResearchError):
    """Raised when input validation fails."""

    pass