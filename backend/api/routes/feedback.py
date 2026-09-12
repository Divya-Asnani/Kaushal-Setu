"""/feedback — the customer rating for a completed job.

Ratings are a trust signal shown alongside matches. They are deliberately not an input
to the ranking formula (PRD section 15: rating must never be the sole matching
criterion, and experience relevance is what the product is about).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.api.deps import CurrentUser, get_current_user
from backend.core.errors import APIError, CONFLICT, forbidden, not_found
from backend.db.supabase import one_or_none, rows, table
from backend.schemas.models import FeedbackIn, FeedbackOut
from backend.services.jobs import lifecycle

router = APIRouter(tags=["feedback"])


def _to_out(row: dict) -> FeedbackOut:
    return FeedbackOut(
        id=str(row["id"]),
        job_id=str(row["job_id"]),
        customer_id=str(row["customer_id"]),
        worker_id=str(row["worker_id"]),
        rating=float(row["rating"]),
        feedback_text=row.get("feedback_text"),
    )


@router.post("/feedback", response_model=FeedbackOut, status_code=201)
def submit_feedback(
    payload: FeedbackIn,
    user: CurrentUser = Depends(get_current_user),
) -> FeedbackOut:
    context = lifecycle.load_job_participants(payload.job_id)
    if context is None:
        raise not_found("Job")
    if not user.owns(context["customer_id"]) and not user.is_admin:
        raise forbidden("Only the customer on this job can leave feedback.")
    if (context["job"].get("status") or "") not in {"completed", "disputed"}:
        raise APIError(CONFLICT, "Feedback can only be left once the job is complete.")

    existing = one_or_none(
        table("feedback").select("id").eq("job_id", payload.job_id).limit(1).execute()
    )
    if existing is not None:
        raise APIError(CONFLICT, "Feedback has already been submitted for this job.")

    created = rows(
        table("feedback")
        .insert(
            {
                "job_id": payload.job_id,
                "customer_id": context["customer_id"],
                "worker_id": context["worker_id"],
                "rating": payload.rating,
                "feedback_text": payload.feedback_text,
            }
        )
        .execute()
    )[0]
    return _to_out(created)


@router.get("/jobs/{job_id}/feedback", response_model=FeedbackOut | None)
def get_job_feedback(
    job_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> FeedbackOut | None:
    context = lifecycle.load_job_participants(job_id)
    if context is None:
        raise not_found("Job")
    is_participant = user.owns(context["customer_id"]) or user.owns(context["worker_id"])
    if not is_participant and not user.is_admin:
        raise forbidden("You are not a participant in this job.")

    row = one_or_none(table("feedback").select("*").eq("job_id", job_id).limit(1).execute())
    return _to_out(row) if row else None
