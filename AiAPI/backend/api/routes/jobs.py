"""/jobs — job lifecycle, completion with evidence, verification and disputes."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query

from backend.api.deps import CurrentUser, get_current_user
from backend.core.errors import APIError, CONFLICT, forbidden, not_found
from backend.db.supabase import one_or_none, rows, table
from backend.schemas.models import (
    CompletionIn,
    CompletionOut,
    DisputeIn,
    JobOut,
    JobStatusPatch,
    VerificationOut,
    VerifyIn,
)
from backend.services.ai import indexing
from backend.services.graph import neo4j_client
from backend.services.jobs import lifecycle
from backend.services.storage import storage
from backend.services.notifications import notify as notifications

log = logging.getLogger(__name__)
router = APIRouter(tags=["jobs"])


def _load(job_id: str) -> dict[str, Any]:
    context = lifecycle.load_job_participants(job_id)
    if context is None:
        raise not_found("Job")
    return context


def _assert_participant(context: dict[str, Any], user: CurrentUser) -> None:
    if user.is_admin:
        return
    if user.owns(context.get("customer_id")) or user.owns(context.get("worker_id")):
        return
    raise forbidden("You are not a participant in this job.")


def _to_out(job: dict[str, Any], include_history: bool = True) -> JobOut:
    history = []
    if include_history:
        history = rows(
            table("job_status_history")
            .select("status, notes, changed_at")
            .eq("job_id", job["id"])
            .order("changed_at")
            .execute()
        )
    return JobOut(
        id=str(job["id"]),
        service_request_id=str(job["service_request_id"]),
        status=job.get("status") or "confirmed",
        scheduled_at=job.get("scheduled_at"),
        started_at=job.get("started_at"),
        completed_at=job.get("completed_at"),
        status_history=history,
    )


@router.get("/jobs", response_model=list[JobOut])
def list_my_jobs(
    limit: int = Query(default=20, ge=1, le=100),
    user: CurrentUser = Depends(get_current_user),
) -> list[JobOut]:
    """Jobs the caller participates in, resolved through their service requests."""
    if user.role == "worker":
        request_ids = [
            str(r["id"])
            for r in rows(
                table("service_requests").select("id").eq("worker_id", user.id).execute()
            )
        ]
    else:
        problem_ids = [
            str(p["id"])
            for p in rows(table("problems").select("id").eq("customer_id", user.id).execute())
        ]
        if not problem_ids:
            return []
        request_ids = [
            str(r["id"])
            for r in rows(
                table("service_requests").select("id").in_("problem_id", problem_ids).execute()
            )
        ]
    if not request_ids:
        return []

    jobs = rows(
        table("jobs")
        .select("*")
        .in_("service_request_id", request_ids)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return [_to_out(j, include_history=False) for j in jobs]


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: str, user: CurrentUser = Depends(get_current_user)) -> JobOut:
    context = _load(job_id)
    _assert_participant(context, user)
    return _to_out(context["job"])


@router.patch("/jobs/{job_id}/status", response_model=JobOut)
def update_job_status(
    job_id: str,
    payload: JobStatusPatch,
    user: CurrentUser = Depends(get_current_user),
) -> JobOut:
    context = _load(job_id)
    _assert_participant(context, user)

    if payload.status == "completed":
        raise APIError(
            CONFLICT,
            "Complete a job through POST /jobs/{job_id}/completion so the outcome and "
            "evidence are recorded with it.",
        )
    if payload.status == "in_progress" and not (
        user.owns(context["worker_id"]) or user.is_admin
    ):
        raise forbidden("Only the assigned worker can start this job.")

    job = lifecycle.change_job_status(context["job"], payload.status, user.id, payload.notes)
    return _to_out(job)


@router.post("/jobs/{job_id}/completion", response_model=CompletionOut, status_code=201)
def submit_completion(
    job_id: str,
    payload: CompletionIn,
    user: CurrentUser = Depends(get_current_user),
) -> CompletionOut:
    """Record diagnosis, actions, outcome and evidence, creating the experience.

    The experience is created as ``submitted``, not ``verified``. Evidence supports a
    claim; only the customer can confirm it (PRD section 15).
    """
    context = _load(job_id)
    job = context["job"]
    if not user.owns(context["worker_id"]) and not user.is_admin:
        raise forbidden("Only the assigned worker can submit completion.")

    existing = one_or_none(
        table("verifications").select("experience_id").eq("job_id", job_id).limit(1).execute()
    )
    if existing and existing.get("experience_id"):
        raise APIError(
            CONFLICT,
            "Completion has already been submitted for this job.",
            {"experience_id": str(existing["experience_id"])},
        )

    if job.get("status") == "confirmed":
        job = lifecycle.change_job_status(job, "in_progress", user.id, "Auto-started on completion.")
    lifecycle.assert_job_transition(job.get("status") or "confirmed", "completed")

    problem = context["problem"] or {}
    experience = rows(
        table("experiences")
        .insert(
            {
                "worker_id": context["worker_id"],
                "title": problem.get("title") or "Completed job",
                "problem_description": problem.get("description") or "",
                "diagnosis": payload.diagnosis,
                "outcome_summary": payload.outcome_summary
                or (payload.outcomes[0].outcome_description if payload.outcomes else None),
                "experience_status": "submitted",
                "verification_confidence": 0,
                "solved_at": lifecycle.iso(),
            }
        )
        .execute()
    )[0]
    experience_id = str(experience["id"])

    from backend.api.routes.experiences import write_experience_children

    write_experience_children(
        experience_id, payload.contexts, payload.actions, payload.outcomes, payload.skill_ids
    )

    if payload.evidence:
        # Keeps unset fields: media_type and media_role default here and back NOT NULL
        # columns, so dropping them on a silent client would be a null violation.
        table("experience_media").insert(
            [
                {
                    **storage.validate_media(storage.EXPERIENCE, e.model_dump()),
                    "experience_id": experience_id,
                    # Evidence is unverified until a customer confirms the outcome.
                    "is_verified": False,
                }
                for e in payload.evidence
            ]
        ).execute()

    lifecycle.change_job_status(job, "completed", user.id, "Completion submitted.")

    table("verifications").insert(
        {
            "job_id": job_id,
            "experience_id": experience_id,
            "verification_type": "customer_confirmation",
            "verification_status": "pending",
        }
    ).execute()

    indexing.index_experience(experience_id)

    notifications.notify(
        user_id=context["customer_id"],
        notification_type="job_completed",
        title="Work marked complete",
        message="The worker submitted their diagnosis and evidence. Please confirm or dispute it.",
        related_entity_type="job",
        related_entity_id=job_id,
    )

    return CompletionOut(
        job_id=job_id,
        status="completed",
        experience_id=experience_id,
        evidence_count=len(payload.evidence),
    )


def _project_to_graph(experience_id: str) -> None:
    """Push a now-verified experience into the Experience Graph. Never raises."""
    experience = one_or_none(
        table("experiences").select("*").eq("id", experience_id).limit(1).execute()
    )
    if experience is None:
        return
    contexts = [
        str(c.get("context_value") or "")
        for c in rows(
            table("experience_contexts")
            .select("context_value")
            .eq("experience_id", experience_id)
            .execute()
        )
    ]
    skills = [
        (s.get("skills") or {}).get("name")
        for s in rows(
            table("experience_skills")
            .select("skills(name)")
            .eq("experience_id", experience_id)
            .execute()
        )
    ]
    neo4j_client.project_experience(
        experience_id=experience_id,
        worker_id=str(experience["worker_id"]),
        title=experience.get("title") or "",
        problem_description=experience.get("problem_description") or "",
        contexts=[c for c in contexts if c],
        skills=[s for s in skills if s],
        verified=True,
    )


@router.post("/jobs/{job_id}/verify", response_model=VerificationOut)
def verify_job(
    job_id: str,
    payload: VerifyIn,
    user: CurrentUser = Depends(get_current_user),
) -> VerificationOut:
    """Customer confirmation. This is the only path that creates verified experience."""
    context = _load(job_id)
    if not user.owns(context["customer_id"]) and not user.is_admin:
        raise forbidden("Only the customer on this job can verify it.")
    if (context["job"].get("status") or "") not in {"completed", "disputed"}:
        raise APIError(CONFLICT, "This job has not been submitted as complete yet.")

    verification = one_or_none(
        table("verifications").select("*").eq("job_id", job_id).limit(1).execute()
    )
    if verification is None:
        raise not_found("Verification record")
    if verification.get("verification_status") == "verified":
        raise APIError(CONFLICT, "This job has already been verified.")

    verified = payload.verification_status == "verified"
    score = 100 if verified else 0

    updated = rows(
        table("verifications")
        .update(
            {
                "verification_status": payload.verification_status,
                "verification_score": score,
                "verifier_id": user.id,
                "comments": payload.comments,
                "verified_at": lifecycle.iso(),
                "updated_at": lifecycle.iso(),
            }
        )
        .eq("id", verification["id"])
        .execute()
    )[0]

    experience_id = (
        str(verification["experience_id"]) if verification.get("experience_id") else None
    )
    if experience_id:
        table("experiences").update(
            {
                "experience_status": "verified" if verified else "submitted",
                "verification_confidence": score,
                "updated_at": lifecycle.iso(),
            }
        ).eq("id", experience_id).execute()
        table("experience_outcomes").update({"customer_confirmed": verified}).eq(
            "experience_id", experience_id
        ).execute()
        if verified:
            table("experience_media").update({"is_verified": True}).eq(
                "experience_id", experience_id
            ).execute()
            # Re-index first: the vector store is what future matching reads.
            indexing.index_experience(experience_id)
            _project_to_graph(experience_id)

    if verified and context["problem"]:
        table("problems").update({"status": "resolved"}).eq(
            "id", context["problem"]["id"]
        ).execute()

    notifications.notify(
        user_id=context["worker_id"],
        notification_type="job_verified" if verified else "job_verification_rejected",
        title="Work confirmed" if verified else "Work not confirmed",
        message=(
            "The customer confirmed your work. It now counts as verified experience."
            if verified
            else "The customer did not confirm this work."
        ),
        related_entity_type="job",
        related_entity_id=job_id,
    )

    return VerificationOut(
        verification_id=str(updated["id"]),
        verification_status=updated["verification_status"],
        verification_score=float(updated["verification_score"]),
        verified_at=updated.get("verified_at"),
        experience_id=experience_id,
    )


@router.post("/jobs/{job_id}/dispute", response_model=VerificationOut)
def dispute_job(
    job_id: str,
    payload: DisputeIn,
    user: CurrentUser = Depends(get_current_user),
) -> VerificationOut:
    """Customer dispute. A disputed case is never treated as verified experience."""
    context = _load(job_id)
    if not user.owns(context["customer_id"]) and not user.is_admin:
        raise forbidden("Only the customer on this job can dispute it.")

    verification = one_or_none(
        table("verifications").select("*").eq("job_id", job_id).limit(1).execute()
    )
    if verification is None:
        raise not_found("Verification record")

    updated = rows(
        table("verifications")
        .update(
            {
                "verification_type": "dispute",
                "verification_status": "disputed",
                "verification_score": 0,
                "verifier_id": user.id,
                "comments": payload.comments,
                "updated_at": lifecycle.iso(),
            }
        )
        .eq("id", verification["id"])
        .execute()
    )[0]

    experience_id = (
        str(verification["experience_id"]) if verification.get("experience_id") else None
    )
    if experience_id:
        table("experiences").update(
            {"experience_status": "disputed", "verification_confidence": 0}
        ).eq("id", experience_id).execute()
        table("experience_outcomes").update({"customer_confirmed": False}).eq(
            "experience_id", experience_id
        ).execute()
        indexing.index_experience(experience_id)

    if (context["job"].get("status") or "") == "completed":
        lifecycle.change_job_status(context["job"], "disputed", user.id, payload.comments)

    notifications.notify(
        user_id=context["worker_id"],
        notification_type="job_disputed",
        title="Work disputed",
        message="The customer disputed this job. It will not count as verified experience.",
        related_entity_type="job",
        related_entity_id=job_id,
    )

    return VerificationOut(
        verification_id=str(updated["id"]),
        verification_status="disputed",
        verification_score=0,
        verified_at=None,
        experience_id=experience_id,
    )
