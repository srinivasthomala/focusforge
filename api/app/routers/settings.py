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
async def get_settings_endpoint(
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SettingsData:
    row = db.get(UserSettings, user_id)
    if row is None:
        # No saved settings yet — hand back the defaults (no row created on read).
        return SettingsData(blocklist=list(DEFAULT_BLOCKLIST), blockingMode="focus-only")
    return _to_data(row)


@router.put("", response_model=SettingsData)
async def put_settings_endpoint(
    payload: SettingsData,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SettingsData:
    blocklist = normalize_blocklist(payload.blocklist)
    blocklist_json = json.dumps(blocklist)

    row = db.get(UserSettings, user_id)
    if row is None:
        row = UserSettings(
            user_id=user_id,
            blocklist=blocklist_json,
            blocking_mode=payload.blockingMode,
        )
        db.add(row)
    else:
        row.blocklist = blocklist_json
        row.blocking_mode = payload.blockingMode
    db.commit()

    return SettingsData(blocklist=blocklist, blockingMode=payload.blockingMode)
