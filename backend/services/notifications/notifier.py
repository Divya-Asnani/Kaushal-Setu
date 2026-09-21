import uuid
from datetime import datetime, timezone
from typing import Optional
from backend.config import IST
from backend.db.supabase_client import db

def send_notification(
    user_id: str,
    title: str,
    message: str,
    notification_type: str,
    reference_id: Optional[str] = None
) -> str:
    """Dispatches in-app notification to the notifications table."""
    now = datetime.now(IST)
    notif_id = str(uuid.uuid4())
    notif_record = {
        "id": notif_id,
        "user_id": str(user_id),
        "title": title,
        "message": message,
        "notification_type": notification_type,
        "related_entity_id": str(reference_id) if reference_id else None,
        "is_read": False,
        "created_at": now
    }
    db.notifications[notif_id] = notif_record
    db.sync_to_supabase("notifications", notif_record)
    return notif_id
