"""Authentication — resolve a request to a ``user_id``.

Two credential types, both presented as ``Authorization: Bearer <token>``:

- **Supabase JWT** — the web dashboard, after an interactive magic-link login.
- **FocusForge API key** (prefixed ``ff_``) — the browser extension and any
  other device/headless client.

This is the API-first split: humans authenticate with a short-lived session JWT,
devices authenticate with a long-lived API key, and both resolve to the same
``user_id`` so every endpoint stays client-agnostic.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone

import jwt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.db_models import ApiKey

API_KEY_PREFIX = "ff_"
_SUPABASE_AUDIENCE = "authenticated"


def hash_api_key(raw: str) -> str:
    """API keys are high-entropy random tokens, so a plain SHA-256 is sufficient
    (no need for a slow password hash)."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def generate_api_key() -> tuple[str, str, str]:
    """Return ``(raw_key, key_hash, display_prefix)``. The raw key is returned to
    the user once and never stored."""
    raw = API_KEY_PREFIX + secrets.token_urlsafe(32)
    return raw, hash_api_key(raw), raw[:11]


def _user_from_api_key(token: str, db: Session) -> str | None:
    if not token.startswith(API_KEY_PREFIX):
        return None
    row = db.scalars(
        select(ApiKey).where(ApiKey.key_hash == hash_api_key(token))
    ).first()
    if row is None:
        return None
    row.last_used_at = datetime.now(timezone.utc)
    db.commit()
    return row.user_id


_jwks_client: jwt.PyJWKClient | None = None


def _get_jwks_client() -> jwt.PyJWKClient | None:
    """Lazily build (and cache) a JWKS client for the Supabase project. Returns
    None when SUPABASE_URL is unset. PyJWKClient caches fetched keys internally."""
    global _jwks_client
    if _jwks_client is None:
        url = get_settings().supabase_jwks_url
        if not url:
            return None
        _jwks_client = jwt.PyJWKClient(url)
    return _jwks_client


def _user_from_jwt(token: str) -> str | None:
    settings = get_settings()
    try:
        alg = jwt.get_unverified_header(token).get("alg")
    except jwt.PyJWTError:
        return None

    try:
        if alg in ("ES256", "RS256"):
            # Modern Supabase: verify against the project's published public key.
            client = _get_jwks_client()
            if client is None:
                return None
            key = client.get_signing_key_from_jwt(token).key
            payload = jwt.decode(
                token, key, algorithms=[alg], audience=_SUPABASE_AUDIENCE
            )
        elif alg == "HS256":
            # Legacy Supabase: shared-secret verification.
            secret = settings.supabase_jwt_secret
            if not secret:
                return None
            payload = jwt.decode(
                token, secret, algorithms=["HS256"], audience=_SUPABASE_AUDIENCE
            )
        else:
            return None
    except (jwt.PyJWTError, jwt.PyJWKClientError):
        return None
    return payload.get("sub")


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> str:
    """FastAPI dependency: resolve the bearer token to a ``user_id`` or raise 401."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header.",
        )
    token = authorization.split(" ", 1)[1].strip()
    # API key first (cheap prefix check), then fall back to verifying a JWT.
    user_id = _user_from_api_key(token, db) or _user_from_jwt(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired credentials.",
        )
    return user_id
