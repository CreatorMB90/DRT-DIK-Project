from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # Shopify
    SHOPIFY_API_SECRET: str

    # Supabase
    DATABASE_URL: str = ""
    SUPABASE_URL: str
    SUPABASE_KEY: str

    # LLM / AI — DeepSeek (OpenAI-compatible)
    LLM_API_KEY: str = Field(
        default="",
        validation_alias="DEEPSEEK_API_KEY",
        description="DeepSeek API key",
    )
    LLM_BASE_URL: str = Field(
        default="https://api.deepseek.com/v1",
        validation_alias="DEEPSEEK_BASE_URL",
        description="DeepSeek API base URL (OpenAI-compatible endpoint)",
    )
    LLM_MODEL: str = "deepseek-chat"


settings = Settings()
