import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from backend.api.deps import CurrentUser, get_current_user
from backend.db.supabase_client import db
from backend.schemas.notification import NotificationRead, NotificationMarkRead
from backend.schemas.worker import SkillRead
from backend.schemas.common import AppException

router = APIRouter(tags=["Notifications & Common"])

@router.get("/notifications", response_model=List[NotificationRead])
def list_my_notifications(current_user: CurrentUser = Depends(get_current_user)):
    user_id_str = str(current_user.id)
    user_notifs = [
        n for n in db.notifications.values()
        if str(n.get("user_id")) == user_id_str
    ]
    user_notifs.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
    return [
        {
            **n,
            "type": n.get("type") or n.get("notification_type", "general"),
            "reference_id": n.get("reference_id") or n.get("related_entity_id")
        }
        for n in user_notifs
    ]

@router.patch("/notifications/{id}/read", response_model=NotificationRead)
def mark_notification_as_read(id: uuid.UUID, current_user: CurrentUser = Depends(get_current_user)):
    notif_id_str = str(id)
    notif = db.notifications.get(notif_id_str)
    if not notif:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="RESOURCE_NOT_FOUND",
            message="Notification not found."
        )

    if str(notif.get("user_id")) != str(current_user.id):
        raise AppException(
            status_code=status.HTTP_403_FORBIDDEN,
            code="FORBIDDEN",
            message="You cannot modify another user's notifications."
        )

    notif["is_read"] = True
    db.sync_to_supabase("notifications", notif)
    return {
        **notif,
        "type": notif.get("type") or notif.get("notification_type", "general"),
        "reference_id": notif.get("reference_id") or notif.get("related_entity_id")
    }

@router.get("/skills", response_model=List[SkillRead])
def list_skills():
    """Lists all standard platform skills."""
    return list(db.skills.values())
