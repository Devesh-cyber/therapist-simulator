"""Application settings loaded from environment variables / .env."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Grok (xAI) ---
    grok_api_key: str = ""
    grok_model: str = "grok-4"
    grok_base_url: str = "https://api.x.ai/v1"
    grok_timeout_seconds: float = 60.0

    # "grok" uses the real API. "mock" uses the offline demo engine (no key needed).
    # "auto" (default) = grok when GROK_API_KEY is set, otherwise mock.
    llm_mode: str = "auto"

    # --- Database ---
    # Supabase: Project Settings -> Database -> Connection string (URI), e.g.
    # postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres
    # Leave empty for local SQLite development.
    database_url: str = ""

    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    # --- App ---
    app_secret: str = "change-me-in-production"
    frontend_url: str = "http://localhost:5173"
    session_minutes: int = 10
    max_message_chars: int = 800

    @property
    def effective_llm_mode(self) -> str:
        if self.llm_mode in ("grok", "mock"):
            return self.llm_mode
        return "grok" if self.grok_api_key else "mock"

    @property
    def sqlalchemy_url(self) -> str:
        url = self.database_url.strip()
        if not url:
            return "sqlite:///./therapist_sim.db"
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                url = "postgresql+psycopg://" + url[len(prefix):]
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
