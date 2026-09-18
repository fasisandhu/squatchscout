from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./dev.db"
    groq_api_key: str | None = None
    groq_models: Annotated[list[str], NoDecode] = Field(
        default=["qwen/qwen3.8-27b", "openai/gpt-oss-20b"]
    )
    llm_daily_soft_cap: int = 600
    frontend_origins: Annotated[list[str], NoDecode] = Field(default=["http://localhost:5173"])
    crawler_user_agent: str = "SquatchScoutBot/0.1 (+{public_url}/about)"
    crawler_contact: str | None = None
    public_url: str = "http://localhost:5173"
    overpass_endpoints: Annotated[list[str], NoDecode] = Field(
        default=[
            "https://overpass-api.de/api/interpreter",
            "https://overpass.kumi.systems/api/interpreter",
        ]
    )
    nominatim_endpoint: str = "https://nominatim.openstreetmap.org"
    max_leads_per_search: int = 60
    purge_after_days: int = 30
    api_host: str | None = None
    enrich_cache_ttl_days: int = 7
    overpass_cache_ttl_hours: int = 24
    log_level: str = "INFO"
    app_version: str = "dev"

    @field_validator("groq_models", "frontend_origins", "overpass_endpoints", mode="before")
    @classmethod
    def _split_csv(cls, v):
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v

    @property
    def llm_enabled(self) -> bool:
        return bool(self.groq_api_key)

    @property
    def user_agent(self) -> str:
        ua = self.crawler_user_agent.format(public_url=self.public_url)
        return f"{ua} contact: {self.crawler_contact}" if self.crawler_contact else ua


@lru_cache
def get_settings() -> Settings:
    return Settings()
