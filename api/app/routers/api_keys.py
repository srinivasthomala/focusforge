from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import generate_api_key, get_current_user
from app.database import get_db
from app.db_models import ApiKey
from app.models import ApiKeyCreateRequest, ApiKeyCreateResponse, ApiKeyInfo

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _to_info(row: ApiKey) -> ApiKeyInfo:
    return ApiKeyInfo(
        id=row.id,
        prefix=row.prefix,
        label=row.label or "",
        createdAt=_iso(row.created_at),
        lastUsedAt=_iso(row.last_used_at),
    )


@router.get("", response_model=list[ApiKeyInfo])
async def list_api_keys(
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ApiKeyInfo]:
    rows = db.scalars(
        select(ApiKey)
        .where(ApiKey.user_id == user_id)
        .order_by(ApiKey.created_at.desc())
    ).all()
    return [_to_info(r) for r in rows]


@router.post("", response_model=ApiKeyCreateResponse)
async def create_api_key(
    payload: ApiKeyCreateRequest,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiKeyCreateResponse:
    raw, key_hash, prefix = generate_api_key()
    row = ApiKey(
        user_id=user_id,
        key_hash=key_hash,
        prefix=prefix,
        label=payload.label or "",
        created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ApiKeyCreateResponse(key=raw, **_to_info(row).model_dump())


@router.delete("/{key_id}", status_code=204)
async def delete_api_key(
    key_id: int,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    row = db.scalars(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user_id)
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="API key not found.")
    db.delete(row)
    db.commit()
