import logging

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.models import LogBatch
from app.database import get_db
from app.db_models import ActivityLog, log_entry_to_orm

router = APIRouter()
log = logging.getLogger(__name__)


def _user_log_count(db: Session, user_id: str) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(ActivityLog)
            .where(ActivityLog.user_id == user_id)
        )
        or 0
    )


@router.post("/logs")
def receive_logs(
    batch: LogBatch,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Receive a batch of activity logs from a device client (e.g. the Chrome
    extension) and persist them, scoped to the authenticated user.
    """
    try:
        rows = []
        for e in batch.logs:
            row = log_entry_to_orm(e)
            row.user_id = user_id  # never trust a client-supplied userId
            rows.append(row)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid log timestamp: {e}")

    try:
        db.add_all(rows)
        db.commit()
        return {
            "status": "success",
            "received": len(batch.logs),
            "total_stored": _user_log_count(db, user_id),  # this user's rows only
        }
    except Exception:
        db.rollback()
        # Log the real error server-side; never echo DB internals to clients.
        log.exception("failed to store %d logs for user %s", len(rows), user_id)
        raise HTTPException(status_code=500, detail="Could not store logs. Please retry.")


@router.get("/logs/count")
def get_log_count(
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the count of stored log rows for the authenticated user."""
    return {"count": _user_log_count(db, user_id)}
