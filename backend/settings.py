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

    # pydantic-settings config
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()