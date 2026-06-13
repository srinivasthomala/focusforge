from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # postgresql+psycopg2://user:pass@host:5432/dbname
    database_url: str = "postgresql+psycopg2://focusforge:focusforge@localhost:5432/focusforge"

    # Optional — enables real AI summaries via Anthropic Claude. When unset, the
    # API serves a deterministic fallback so the demo still works.
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-4-8"

    # Abuse guards for the public demo (only real Claude calls count against these).
    ai_daily_generation_limit: int = 50  # hard ceiling per UTC day across all users
    ai_rate_limit_per_ip: int = 5  # max generations per IP within the window
    ai_rate_limit_window_seconds: int = 3600  # the per-IP window (1 hour)

    # Supabase auth — the project's JWT secret (Settings -> API -> JWT Secret).
    # Used to verify dashboard access tokens (HS256). The extension authenticates
    # with FocusForge API keys instead, so it doesn't need this.
    supabase_jwt_secret: str = ""

    # Comma-separated list of origins allowed by CORS. Defaults to the local web
    # dev server; in prod set this to the deployed web origin(s), e.g.
    # CORS_ALLOWED_ORIGINS=https://focusforge.vercel.app
    cors_allowed_origins: str = "http://localhost:3000"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    @property
    def sync_database_url(self) -> str:
        url = self.database_url
        if url.startswith("postgres://"):
            return "postgresql+psycopg2://" + url[len("postgres://") :]
        if url.startswith("postgresql://") and "psycopg2" not in url.split("://", 1)[0]:
            return "postgresql+psycopg2://" + url[len("postgresql://") :]
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
