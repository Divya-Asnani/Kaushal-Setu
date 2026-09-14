"""/notifications — the caller's in-app notifications."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from backend.api.deps import CurrentUser, get_current_user
from backend.core.errors import forbidden, not_found
from backend.db.supabase import one_or_none, rows, table
from backend.schemas.models import NotificationOut
from backend.services.jobs import lifecycle

router = APIRouter(tags=["notifications"])


def _to_out(row: dict) -> NotificationOut:
    return NotificationOut(
        id=str(row["id"]),
        notification_type=row.get("notification_type") or "",
        title=row.get("title") or "",
        message=row.get("message") or "",
        related_entity_type=row.get("related_entity_type"),
        related_entity_id=str(row["related_entity_id"]) if row.get("related_entity_id") else None,
        is_read=bool(row.get("is_read")),
        read_at=row.get("read_at"),
        created_at=row.get("created_at"),
    )


@router.get("/notifications", response_model=list[NotificationOut])
def list_notifications(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    unread_only: bool = Query(default=False),
    user: CurrentUser = Depends(get_current_user),
) -> list[NotificationOut]:
    builder = table("notifications").select("*").eq("user_id", user.id)
    if unread_only:
        builder = builder.eq("is_read", False)
    result = rows(
        builder.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    )
    return [_to_out(r) for r in result]


@router.patch("/notifications/{notification_id}/read", response_model=NotificationOut)
def mark_read(
    notification_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> NotificationOut:
    row = one_or_none(
        table("notifications").select("*").eq("id", notification_id).limit(1).execute()
    )
    if row is None:
        raise not_found("Notification")
    if not user.owns(str(row["user_id"])):
        raise forbidden("This notification belongs to another user.")

    updated = rows(
        table("notifications")
        .update({"is_read": True, "read_at": lifecycle.iso()})
        .eq("id", notification_id)
        .execute()
    )[0]
    return _to_out(updated)
