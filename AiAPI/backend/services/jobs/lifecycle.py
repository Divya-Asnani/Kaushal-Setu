"""Job and service-request state machines (FastAPI spec section 9).

Transitions are declared as data rather than scattered through route handlers, so an
invalid move is rejected in one place and the rules stay readable.

Every job transition writes a job_status_history row. PostgREST has no multi-statement
transaction, so the history row is written immediately after the status update and a
failure there is loud: the audit trail is the point of the table.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.core.config import settings
from backend.core.errors import invalid_transition
from backend.db.supabase import rows, table

log = logging.getLogger(__name__)

JOB_TRANSITIONS: dict[str, set[str]] = {
    "confirmed": {"in_progress", "cancelled"},
    "in_progress": {"completed", "cancelled"},
    "completed": {"disputed"},
    "cancelled": set(),
    "disputed": {"completed"},
}

REQUEST_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"accepted", "rejected", "cancelled", "expired"},
    "accepted": set(),
    "rejected": set(),
    "cancelled": set(),
    "expired": set(),
}


def now() -> datetime:
    return datetime.now(timezone.utc)


def iso(moment: datetime | None = None) -> str:
    return (moment or now()).isoformat()


def request_expiry() -> str:
    return iso(now() + timedelta(hours=settings.service_request_ttl_hours))


def assert_job_transition(current: str, requested: str) -> None:
    if requested not in JOB_TRANSITIONS.get(current, set()):
        raise invalid_transition(current, requested)


def assert_request_transition(current: str, requested: str) -> None:
    if requested not in REQUEST_TRANSITIONS.get(current, set()):
        raise invalid_transition(current, requested)


def change_job_status(
    job: dict[str, Any],
    new_status: str,
    changed_by: str | None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Validate, apply and record a job status change."""
    current = job.get("status") or "confirmed"
    assert_job_transition(current, new_status)

    update: dict[str, Any] = {"status": new_status, "updated_at": iso()}
    if new_status == "in_progress" and not job.get("started_at"):
        update["started_at"] = iso()
    if new_status == "completed":
        update["completed_at"] = iso()

    updated = rows(table("jobs").update(update).eq("id", job["id"]).execute())

    table("job_status_history").insert(
        {
            "job_id": job["id"],
            "status": new_status,
            "changed_by": str(changed_by) if changed_by else None,
            "notes": notes,
        }
    ).execute()

    return updated[0] if updated else {**job, **update}


def load_job_participants(job_id: str) -> dict[str, Any] | None:
    """Resolve job -> service_request -> problem, giving the customer and worker ids.

    Authorization for every job-scoped endpoint depends on this, so it is a single
    helper rather than a join repeated per route.
    """
    job = (rows(table("jobs").select("*").eq("id", job_id).limit(1).execute()) or [None])[0]
    if job is None:
        return None

    request = (
        rows(
            table("service_requests")
            .select("*")
            .eq("id", job["service_request_id"])
            .limit(1)
            .execute()
        )
        or [None]
    )[0]
    if request is None:
        return {"job": job, "request": None, "problem": None,
                "customer_id": None, "worker_id": None}

    problem = (
        rows(table("problems").select("*").eq("id", request["problem_id"]).limit(1).execute())
        or [None]
    )[0]

    return {
        "job": job,
        "request": request,
        "problem": problem,
        "customer_id": str(problem["customer_id"]) if problem else None,
        "worker_id": str(request["worker_id"]),
    }
