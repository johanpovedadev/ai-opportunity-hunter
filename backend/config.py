from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "postgresql+asyncpg://user:pass@localhost:5432/opportunity_hunter"

    # AI Provider: "gemini" or "openai"
    ai_provider: Literal["gemini", "openai"] = "openai"

    # Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash-lite"

    # OpenAI / LM Studio
    openai_base_url: str = "http://localhost:1234/v1"
    openai_api_key: str = "lm-studio"
    openai_model: str = ""

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    scrape_linkedin: bool = True
    scrape_wellfound: bool = True
    scrape_getonboard: bool = True
    scrape_computrabajo: bool = True
    scrape_indeed: bool = True
    search_keywords: str = "python developer,backend engineer,software engineer"
    score_threshold: float = 7.0
    schedule_interval_hours: int = 6

    @property
    def keywords_list(self) -> list[str]:
        return [k.strip() for k in self.search_keywords.split(",") if k.strip()]


settings = Settings()
