"""In-app notifications.

MVP notifications are rows, not pushes. They are best-effort: a failure to notify must
never fail the state transition that triggered it.
"""
from __future__ import annotations

import logging
from typing import Any

from backend.db.supabase import table

log = logging.getLogger(__name__)


def notify(
    user_id: str,
    notification_type: str,
    title: str,
    message: str,
    related_entity_type: str | None = None,
    related_entity_id: str | None = None,
) -> None:
    try:
        table("notifications").insert(
            {
                "user_id": str(user_id),
                "notification_type": notification_type,
                "title": title,
                "message": message,
                "related_entity_type": related_entity_type,
                "related_entity_id": str(related_entity_id) if related_entity_id else None,
            }
        ).execute()
    except Exception:
        log.warning("Could not create '%s' notification for %s", notification_type, user_id,
                    exc_info=True)


def notify_many(entries: list[dict[str, Any]]) -> None:
    for entry in entries:
        notify(**entry)
