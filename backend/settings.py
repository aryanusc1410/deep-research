import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env early
load_dotenv()

class Settings(BaseSettings):
    OPENAI_API_KEY: str | None = None
    GOOGLE_API_KEY: str | None = None
    TAVILY_API_KEY: str | None = None
    SERP_API_KEY: str | None = None
    MODEL: str = "gpt-4o-mini"
    MAX_MESSAGES: int = 12
    MAX_SEARCHES: int = 12
    USE_DUAL_SEARCH: bool = True

    GEMINI_MAX_OUTPUT_TOKENS: int = 2048 
    GEMINI_TIMEOUT_SECONDS: int = 30 
    GEMINI_REQUEST_TIMEOUT: int = 45
    GEMINI_MAX_RETRIES: int = 1
    GEMINI_MAX_SEARCHES: int = 4

    # pydantic-settings config
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def get_available_provider(self, requested_provider: str) -> str:
        """
        Returns a valid provider, falling back to OpenAI if requested provider unavailable.
        
        Fallback logic:
        1. If Gemini requested but no GOOGLE_API_KEY → fallback to OpenAI
        2. If OpenAI requested but no OPENAI_API_KEY → raise error (no fallback)
        """
        if requested_provider == "gemini":
            if not self.GOOGLE_API_KEY:
                print("[Settings] ⚠️  GOOGLE_API_KEY not found, falling back to OpenAI")
                if not self.OPENAI_API_KEY:
                    raise ValueError(
                        "Cannot use Gemini (no GOOGLE_API_KEY) and cannot fallback to OpenAI (no OPENAI_API_KEY). "
                        "Please provide at least one of these API keys in your .env file."
                    )
                return "openai"
            return "gemini"
        
        # For openai or any other provider
        if not self.OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY is required. Please add it to your .env file. "
                "Get one at: https://platform.openai.com/api-keys"
            )
        return "openai"

    def validate_search_requirements(self) -> None:
        """
        Validate that at least Tavily API key exists for search.
        """
        if not self.TAVILY_API_KEY:
            raise ValueError(
                "TAVILY_API_KEY is required for search functionality. "
                "Please add it to your .env file. Get one at: https://tavily.com"
            )

    @property
    def has_serp_api(self) -> bool:
        """Check if SerpAPI is available"""
        return bool(self.SERP_API_KEY)

    @property
    def has_gemini(self) -> bool:
        """Check if Gemini is available"""
        return bool(self.GOOGLE_API_KEY)

    @property
    def can_use_dual_search(self) -> bool:
        """Check if dual search is possible"""
        return self.USE_DUAL_SEARCH and self.has_serp_api and bool(self.TAVILY_API_KEY)

settings = Settings()