"""
Application settings and configuration management.

This module handles loading and validating all configuration settings
from environment variables, with support for provider fallback logic
and search tool availability checks.
"""

import os
from typing import Literal

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

from constants import (
    DEFAULT_OPENAI_MODEL,
    DEFAULT_MAX_MESSAGES,
    DEFAULT_MAX_SEARCHES,
    GEMINI_MAX_OUTPUT_TOKENS_DEFAULT,
    GEMINI_TIMEOUT_SECONDS_DEFAULT,
    GEMINI_REQUEST_TIMEOUT_DEFAULT,
    GEMINI_MAX_RETRIES_DEFAULT,
    GEMINI_MAX_SEARCHES_DEFAULT,
    PROVIDER_OPENAI,
    PROVIDER_GEMINI,
)
from exceptions import APIKeyError

# Load environment variables from .env file
load_dotenv()


Provider = Literal["openai", "gemini"]


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    This class uses Pydantic for automatic validation and type conversion
    of environment variables. Settings are loaded from a .env file and
    can be overridden by system environment variables.
    """

    # ========================================================================
    # API Keys
    # ========================================================================

    OPENAI_API_KEY: str | None = None
    """OpenAI API key for GPT models."""

    GEMINI_API_KEY: str | None = None
    """Google Gemini API key."""

    TAVILY_API_KEY: str | None = None
    """Tavily search API key (required for search functionality)."""

    SERP_API_KEY: str | None = None
    """SerpAPI key for additional search functionality (optional)."""

    # ========================================================================
    # General Configuration
    # ========================================================================

    MODEL: str = DEFAULT_OPENAI_MODEL
    """Default model to use for OpenAI."""

    MAX_MESSAGES: int = DEFAULT_MAX_MESSAGES
    """Maximum number of messages to keep in rolling memory buffer."""

    MAX_SEARCHES: int = DEFAULT_MAX_SEARCHES
    """Maximum number of search queries allowed per request."""

    USE_DUAL_SEARCH: bool = True
    """Whether to enable dual search (Tavily + SerpAPI) mode."""

    # ========================================================================
    # Gemini-Specific Configuration
    # ========================================================================

    GEMINI_MAX_OUTPUT_TOKENS: int = GEMINI_MAX_OUTPUT_TOKENS_DEFAULT
    """Maximum number of output tokens for Gemini responses."""

    GEMINI_TIMEOUT_SECONDS: int = GEMINI_TIMEOUT_SECONDS_DEFAULT
    """Timeout in seconds for Gemini API calls."""

    GEMINI_REQUEST_TIMEOUT: int = GEMINI_REQUEST_TIMEOUT_DEFAULT
    """Overall request timeout for Gemini operations."""

    GEMINI_MAX_RETRIES: int = GEMINI_MAX_RETRIES_DEFAULT
    """Maximum number of retries for failed Gemini requests."""

    GEMINI_MAX_SEARCHES: int = GEMINI_MAX_SEARCHES_DEFAULT
    """Maximum number of searches allowed when using Gemini (quota management)."""

    # ========================================================================
    # Pydantic Configuration
    # ========================================================================

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ========================================================================
    # Provider Management Methods
    # ========================================================================

    def get_available_provider(self, requested_provider: Provider) -> Provider:
        """
        Get an available provider, with automatic fallback logic.

        Implements smart fallback:
        - If Gemini requested but unavailable → fallback to OpenAI
        - If OpenAI requested but unavailable → raise error (no fallback)

        Args:
            requested_provider: The provider the user requested

        Returns:
            The provider to actually use (may be different due to fallback)

        Raises:
            APIKeyError: If the provider is unavailable and no fallback exists
        """
        if requested_provider == PROVIDER_GEMINI:
            if not self.GEMINI_API_KEY:
                print(f"[Settings] ⚠️  GEMINI_API_KEY not found, falling back to {PROVIDER_OPENAI}")
                if not self.OPENAI_API_KEY:
                    raise APIKeyError(
                        f"Cannot use {PROVIDER_GEMINI} (no GEMINI_API_KEY) and cannot fallback to "
                        f"{PROVIDER_OPENAI} (no OPENAI_API_KEY). Please provide at least one API key."
                    )
                return PROVIDER_OPENAI
            return PROVIDER_GEMINI

        # For OpenAI or any other provider
        if not self.OPENAI_API_KEY:
            raise APIKeyError(
                "OPENAI_API_KEY is required. Please add it to your .env file. "
                "Get one at: https://platform.openai.com/api-keys"
            )
        return PROVIDER_OPENAI

    def validate_search_requirements(self) -> None:
        """
        Validate that required search API keys are available.

        At minimum, Tavily API key is required for search functionality.

        Raises:
            APIKeyError: If Tavily API key is missing
        """
        if not self.TAVILY_API_KEY:
            raise APIKeyError(
                "TAVILY_API_KEY is required for search functionality. "
                "Please add it to your .env file. Get one at: https://tavily.com"
            )

    # ========================================================================
    # Availability Check Properties
    # ========================================================================

    @property
    def has_serp_api(self) -> bool:
        """Check if SerpAPI is configured and available."""
        return bool(self.SERP_API_KEY)

    @property
    def has_gemini(self) -> bool:
        """Check if Gemini API is configured and available."""
        return bool(self.GEMINI_API_KEY)

    @property
    def has_tavily(self) -> bool:
        """Check if Tavily API is configured and available."""
        return bool(self.TAVILY_API_KEY)

    @property
    def can_use_dual_search(self) -> bool:
        """
        Check if dual search mode is possible.

        Dual search requires:
        1. USE_DUAL_SEARCH flag enabled
        2. Both Tavily and SerpAPI keys available
        """
        return self.USE_DUAL_SEARCH and self.has_serp_api and self.has_tavily


# Global settings instance
settings = Settings()