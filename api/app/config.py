from functools import lru_cache

from pydantic import AliasChoices, Field
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
    # Max generations per signed-in user within the window. Keyed on the user,
    # not the IP: headers like X-Forwarded-For are client-controlled, and web
    # traffic reaches the API through Vercel, so IPs are shared anyway. The old
    # AI_RATE_LIMIT_PER_IP env name is still accepted.
    ai_rate_limit_per_user: int = Field(
        5,
        validation_alias=AliasChoices("ai_rate_limit_per_user", "ai_rate_limit_per_ip"),
    )
    ai_rate_limit_window_seconds: int = 3600  # the per-user window (1 hour)

    # Focus agent (POST /agent/chat). Haiku keeps a free tier affordable; a paid
    # tier can point AGENT_MODEL at a bigger model without code changes.
    agent_model: str = "claude-haiku-5-5"
    agent_effort: str = "medium"  # low | medium | high | xhigh | max
    agent_daily_limit_per_user: int = 5  # questions per user per local day
    agent_daily_limit_global: int = 500  # hard ceiling per UTC day, all users
    agent_max_steps: int = 6  # Claude calls per question (tool round trips)
    agent_deadline_seconds: float = 45.0  # wall clock per question
    agent_max_output_tokens: int = 12000  # summed across a question's calls

    # Supabase auth. The dashboard authenticates with a Supabase access token;
    # the extension uses FocusForge API keys instead, so it needs none of this.
    #
    # Modern Supabase projects sign tokens with asymmetric keys (ES256/RS256),
    # verified via the project's JWKS endpoint — set SUPABASE_URL for that.
    # SUPABASE_JWT_SECRET is the legacy HS256 shared secret, kept as a fallback
    # for projects (or rotations) still signing with it.
    supabase_url: str = ""
    supabase_jwt_secret: str = ""

    @property
    def supabase_jwks_url(self) -> str:
        if not self.supabase_url:
            return ""
        return self.supabase_url.rstrip("/") + "/auth/v1/.well-known/jwks.json"

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
