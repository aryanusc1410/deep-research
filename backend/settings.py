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

    GEMINI_MAX_SEARCHES: int = 6

    # pydantic-settings config
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()