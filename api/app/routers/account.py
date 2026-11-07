"""Account deletion: removes everything stored for the user, then their sign-in.

The database deletes run in one transaction that is committed only after
Supabase confirms the sign-in is gone. If Supabase fails, nothing is deleted
and the user can simply try again.
"""

import logging
import urllib.error
import urllib.request

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.auth import get_current_web_user
from app.config import get_settings
from app.database import get_db
from app.db_models import (
    ActivityLog,
    AgentPendingAction,
    AgentRun,
    AIGenerationEvent,
    AISummary,
    ApiKey,
    UserSettings,
)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/account", tags=["account"])

USER_TABLES = (
    ActivityLog,
    AISummary,
    AIGenerationEvent,
    ApiKey,
    UserSettings,
    AgentRun,
    AgentPendingAction,
)


def delete_supabase_user(user_id: str) -> None:
    """Delete the user's sign-in through the Supabase admin API.

    Raises RuntimeError on failure. A 404 means it's already gone, which is fine.
    """
    settings = get_settings()
    key = settings.supabase_secret_key
    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/admin/users/{user_id}"
    headers = {"apikey": key}
    if not key.startswith("sb_secret_"):
        # Legacy service_role keys are JWTs and go in Authorization as well.
        headers["Authorization"] = f"Bearer {key}"
    request = urllib.request.Request(url, method="DELETE", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=15):
            return
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return
        raise RuntimeError(f"Supabase admin delete returned {e.code}") from e
    except (urllib.error.URLError, TimeoutError) as e:
        raise RuntimeError(f"Supabase admin delete failed: {e}") from e


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    user_id: str = Depends(get_current_web_user),
    db: Session = Depends(get_db),
) -> None:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_secret_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Account deletion isn't available right now. Please contact support.",
        )

    try:
        for table in USER_TABLES:
            db.execute(delete(table).where(table.user_id == user_id))
        delete_supabase_user(user_id)
        db.commit()
    except RuntimeError:
        db.rollback()
        log.exception("account deletion failed at Supabase for %s", user_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Couldn't delete your account right now. Nothing was removed, please try again.",
        )
    except Exception:
        db.rollback()
        log.exception("account deletion failed for %s", user_id)
        raise
    log.info("account deleted: %s", user_id)
