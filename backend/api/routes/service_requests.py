"""/service-requests — a customer asking one worker to take a problem."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query

from backend.api.deps import CurrentUser, get_current_user, require_customer
from backend.core.errors import APIError, CONFLICT, forbidden, not_found
from backend.db.supabase import one_or_none, rows, table
from backend.schemas.models import ServiceRequestIn, ServiceRequestOut, ServiceRequestPatch
from backend.services.jobs import lifecycle
from backend.services.notifications import notify as notifications

log = logging.getLogger(__name__)
router = APIRouter(tags=["service-requests"])

_OPEN_STATUSES = ("pending", "accepted")


def _job_id_for(request_id: str) -> str | None:
    job = one_or_none(
        table("jobs").select("id").eq("service_request_id", request_id).limit(1).execute()
    )
    return str(job["id"]) if job else None


def _to_out(row: dict[str, Any]) -> ServiceRequestOut:
    return ServiceRequestOut(
        id=str(row["id"]),
        problem_id=str(row["problem_id"]),
        worker_id=str(row["worker_id"]),
        status=row.get("status") or "pending",
        match_result_id=(
            str(row["match_result_id"]) if row.get("match_result_id") else None
        ),
        customer_message=row.get("customer_message"),
        worker_response=row.get("worker_response"),
        requested_at=row.get("requested_at"),
        responded_at=row.get("responded_at"),
        accepted_at=row.get("accepted_at"),
        expires_at=row.get("expires_at"),
        job_id=_job_id_for(str(row["id"])),
    )


def _load_with_participants(request_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    request = one_or_none(
        table("service_requests").select("*").eq("id", request_id).limit(1).execute()
    )
    if request is None:
        raise not_found("Service request")
    problem = one_or_none(
        table("problems").select("*").eq("id", request["problem_id"]).limit(1).execute()
    )
    if problem is None:
        raise not_found("Problem")
    return request, problem


@router.post("/service-requests", response_model=ServiceRequestOut, status_code=201)
def create_service_request(
    payload: ServiceRequestIn,
    user: CurrentUser = Depends(require_customer),
) -> ServiceRequestOut:
    problem = one_or_none(
        table("problems").select("*").eq("id", payload.problem_id).limit(1).execute()
    )
    if problem is None:
        raise not_found("Problem")
    if not user.owns(str(problem["customer_id"])):
        raise forbidden("This problem belongs to another customer.")

    worker = one_or_none(
        table("worker_profiles")
        .select("user_id, availability_status")
        .eq("user_id", payload.worker_id)
        .limit(1)
        .execute()
    )
    if worker is None:
        raise not_found("Worker")
    if worker.get("availability_status") == "offline":
        raise APIError(CONFLICT, "This worker is not currently accepting requests.")

    duplicate = rows(
        table("service_requests")
        .select("id, status")
        .eq("problem_id", payload.problem_id)
        .eq("worker_id", payload.worker_id)
        .in_("status", list(_OPEN_STATUSES))
        .execute()
    )
    if duplicate:
        raise APIError(
            CONFLICT,
            "There is already an open request to this worker for this problem.",
            {"service_request_id": str(duplicate[0]["id"])},
        )

    row: dict[str, Any] = {
        "problem_id": payload.problem_id,
        "worker_id": payload.worker_id,
        "status": "pending",
        "customer_message": payload.customer_message,
        "expires_at": lifecycle.request_expiry(),
    }
    if payload.match_result_id:
        # Keeps the audit link from a request back to the ranking that produced it,
        # so the reason a customer chose this worker survives after the fact.
        match = one_or_none(
            table("match_results")
            .select("id, problem_id, worker_id")
            .eq("id", payload.match_result_id)
            .limit(1)
            .execute()
        )
        if match is None:
            raise not_found("Match result")
        if str(match["problem_id"]) != str(payload.problem_id) or str(
            match["worker_id"]
        ) != str(payload.worker_id):
            raise APIError(
                CONFLICT,
                "That match result belongs to a different problem or worker.",
            )
        row["match_result_id"] = payload.match_result_id

    created = rows(table("service_requests").insert(row).execute())[0]

    table("problems").update({"status": "requested"}).eq("id", payload.problem_id).execute()
    notifications.notify(
        user_id=payload.worker_id,
        notification_type="service_request",
        title="New service request",
        message=f"A customer asked you to look at: {problem.get('title')}",
        related_entity_type="service_request",
        related_entity_id=str(created["id"]),
    )
    return _to_out(created)


@router.get("/service-requests", response_model=list[ServiceRequestOut])
def list_service_requests(
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: CurrentUser = Depends(get_current_user),
) -> list[ServiceRequestOut]:
    """Requests the caller participates in: their own as a worker, or via their problems."""
    builder = table("service_requests").select("*")
    if user.role == "worker":
        builder = builder.eq("worker_id", user.id)
    elif not user.is_admin:
        problem_ids = [
            str(p["id"])
            for p in rows(table("problems").select("id").eq("customer_id", user.id).execute())
        ]
        if not problem_ids:
            return []
        builder = builder.in_("problem_id", problem_ids)

    if status:
        builder = builder.eq("status", status)
    result = rows(
        builder.order("requested_at", desc=True).range(offset, offset + limit - 1).execute()
    )
    return [_to_out(r) for r in result]


@router.get("/service-requests/{request_id}", response_model=ServiceRequestOut)
def get_service_request(
    request_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> ServiceRequestOut:
    request, problem = _load_with_participants(request_id)
    is_participant = user.owns(str(problem["customer_id"])) or user.owns(str(request["worker_id"]))
    if not is_participant and not user.is_admin:
        raise forbidden("You are not a participant in this request.")
    return _to_out(request)


@router.patch("/service-requests/{request_id}", response_model=ServiceRequestOut)
def update_service_request(
    request_id: str,
    payload: ServiceRequestPatch,
    user: CurrentUser = Depends(get_current_user),
) -> ServiceRequestOut:
    """Accept, reject, cancel or expire a request.

    Who may make which move is as important as the transition itself: only the worker
    accepts or rejects, and only the customer cancels.
    """
    request, problem = _load_with_participants(request_id)
    customer_id = str(problem["customer_id"])
    worker_id = str(request["worker_id"])
    current = request.get("status") or "pending"
    target = payload.status

    lifecycle.assert_request_transition(current, target)

    is_worker = user.owns(worker_id)
    is_customer = user.owns(customer_id)
    if target in {"accepted", "rejected"} and not (is_worker or user.is_admin):
        raise forbidden("Only the requested worker can accept or reject a request.")
    if target == "cancelled" and not (is_customer or user.is_admin):
        raise forbidden("Only the customer can cancel a request.")
    if target == "expired" and not user.is_admin:
        raise forbidden("Only an administrator can expire a request.")

    updates: dict[str, Any] = {
        "status": target,
        "responded_at": lifecycle.iso(),
        "updated_at": lifecycle.iso(),
    }
    if payload.worker_response is not None:
        updates["worker_response"] = payload.worker_response
    if target == "accepted":
        updates["accepted_at"] = lifecycle.iso()

    updated = rows(
        table("service_requests").update(updates).eq("id", request_id).execute()
    )[0]

    if target == "accepted":
        _accept(request_id, problem, customer_id, worker_id)
    elif target == "rejected":
        _release_problem(problem)
        notifications.notify(
            user_id=customer_id,
            notification_type="service_request_rejected",
            title="Request declined",
            message="The worker is unable to take this job. You can choose another match.",
            related_entity_type="service_request",
            related_entity_id=request_id,
        )
    elif target in {"cancelled", "expired"}:
        _release_problem(problem)

    return _to_out(updated)


def _accept(request_id: str, problem: dict[str, Any], customer_id: str, worker_id: str) -> None:
    """Create the single job for an accepted request and record its first status."""
    existing = one_or_none(
        table("jobs").select("id").eq("service_request_id", request_id).limit(1).execute()
    )
    if existing is not None:
        return  # jobs.service_request_id is UNIQUE; never create a second one.

    job = rows(
        table("jobs").insert({"service_request_id": request_id, "status": "confirmed"}).execute()
    )[0]
    table("job_status_history").insert(
        {"job_id": job["id"], "status": "confirmed", "changed_by": worker_id,
         "notes": "Request accepted."}
    ).execute()

    table("problems").update({"status": "in_progress"}).eq("id", problem["id"]).execute()

    # Other pending requests for the same problem are now moot.
    table("service_requests").update({"status": "expired", "updated_at": lifecycle.iso()}).eq(
        "problem_id", problem["id"]
    ).eq("status", "pending").execute()

    notifications.notify(
        user_id=customer_id,
        notification_type="service_request_accepted",
        title="Request accepted",
        message="A worker accepted your request and a job has been created.",
        related_entity_type="job",
        related_entity_id=str(job["id"]),
    )


def _release_problem(problem: dict[str, Any]) -> None:
    """Return a problem to the matched state when no request is outstanding."""
    outstanding = rows(
        table("service_requests")
        .select("id")
        .eq("problem_id", problem["id"])
        .in_("status", list(_OPEN_STATUSES))
        .execute()
    )
    if not outstanding and problem.get("status") == "requested":
        table("problems").update({"status": "matched"}).eq("id", problem["id"]).execute()
