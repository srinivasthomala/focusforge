"""Per-user settings (blocklist + blocking mode) shared by the web dashboard
and the extension. The dashboard writes them; the extension polls them."""

import json
import re

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.db_models import UserSettings
from app.models import DEFAULT_BLOCKLIST, SettingsData

router = APIRouter(prefix="/settings", tags=["settings"])

_SCHEME_RE = re.compile(r"^https?://")


def normalize_domain(raw: str) -> str:
    """Match the extension's normalization: lowercase host, no scheme/path/www."""
    d = _SCHEME_RE.sub("", str(raw or "").strip().lower())
    d = d.split("/")[0]
    if d.startswith("www."):
        d = d[4:]
    return d


def normalize_blocklist(domains: list[str]) -> list[str]:
    """Normalize, drop blanks, and de-duplicate while preserving order."""
    seen: set[str] = set()
    out: list[str] = []
    for domain in domains:
        d = normalize_domain(domain)
        if d and d not in seen:
            seen.add(d)
            out.append(d)
    return out


def _to_data(row: UserSettings) -> SettingsData:
    return SettingsData(
        blocklist=json.loads(row.blocklist),
        blockingMode=row.blocking_mode,
    )


@router.get("", response_model=SettingsData)
def get_settings_endpoint(
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SettingsData:
    # No saved settings yet: hand back the defaults (no row created on read).
    return load_settings(db, user_id)


def load_settings(db: Session, user_id: str) -> SettingsData:
    row = db.get(UserSettings, user_id)
    if row is None:
        return SettingsData(blocklist=list(DEFAULT_BLOCKLIST), blockingMode="focus-only")
    return _to_data(row)


def save_settings(
    db: Session, user_id: str, blocklist: list[str], blocking_mode: str
) -> SettingsData:
    """Normalize and persist a user's settings (creates the row if needed)."""
    blocklist = normalize_blocklist(blocklist)
    blocklist_json = json.dumps(blocklist)

    row = db.get(UserSettings, user_id)
    if row is None:
        row = UserSettings(
            user_id=user_id,
            blocklist=blocklist_json,
            blocking_mode=blocking_mode,
        )
        db.add(row)
    else:
        row.blocklist = blocklist_json
        row.blocking_mode = blocking_mode
    db.commit()
    return SettingsData(blocklist=blocklist, blockingMode=blocking_mode)


@router.put("", response_model=SettingsData)
def put_settings_endpoint(
    payload: SettingsData,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SettingsData:
    return save_settings(db, user_id, payload.blocklist, payload.blockingMode)
