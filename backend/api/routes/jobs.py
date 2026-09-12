import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, status
from backend.api.deps import (
    CurrentUser, get_current_user, require_worker, check_job_participant, check_job_worker
)
from backend.db.supabase_client import db
from backend.schemas.job import (
    JobRead, JobStatusUpdate, JobCompletionRequest, JobActionItem, JobOutcomeItem, JobEvidenceItem, JobTimelineEvent
)
from backend.services.jobs.lifecycle import transition_job_status, record_job_completion
from backend.services.notifications.notifier import send_notification
from backend.schemas.common import AppException

router = APIRouter(prefix="/jobs", tags=["Jobs"])

def _hydrate_job(job_id_str: str) -> dict:
    job = db.jobs.get(job_id_str)
    if not job:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="RESOURCE_NOT_FOUND",
            message="Job not found."
        )

    problem = db.problems.get(str(job.get("problem_id")), {})
    cust = db.profiles.get(str(job.get("customer_id")), {})
    worker = db.worker_profiles.get(str(job.get("worker_id")), {})
    worker_user = db.profiles.get(str(worker.get("user_id")), {})

    # Hydrate timeline history
    timeline_events = []
    for h in db.job_status_history.values():
        if str(h.get("job_id")) == job_id_str:
            changer = db.profiles.get(str(h.get("changed_by")), {})
            timeline_events.append({
                "id": h["id"],
                "from_status": h.get("from_status"),
                "to_status": h.get("to_status"),
                "changed_by_name": changer.get("full_name", "User"),
                "notes": h.get("notes"),
                "created_at": h.get("created_at")
            })
    timeline_events.sort(key=lambda x: x["created_at"])

    # Hydrate completion details if experience linked
    diagnosis = None
    actions = []
    outcomes = []
    evidence = []
    exp_id_str = str(job.get("experience_id")) if job.get("experience_id") else None

    if exp_id_str and exp_id_str in db.experiences:
        exp = db.experiences[exp_id_str]
        diagnosis = exp.get("diagnosis")
        
        for a in db.experience_actions.values():
            if str(a.get("experience_id")) == exp_id_str:
                actions.append({
                    "step_number": a.get("step_number", 1),
                    "action_type": a.get("action_type", "repair"),
                    "action_description": a.get("action_description", ""),
                    "tools_used": a.get("tools_used", [])
                })
        actions.sort(key=lambda x: x["step_number"])

        for o in db.experience_outcomes.values():
            if str(o.get("experience_id")) == exp_id_str:
                outcomes.append({
                    "outcome_type": o.get("outcome_type", "repair_result"),
                    "outcome_description": o.get("outcome_description", ""),
                    "success_status": o.get("success_status", "successful"),
                    "lessons_learned": o.get("lessons_learned")
                })

        for e in db.experience_media.values():
            if str(e.get("experience_id")) == exp_id_str:
                evidence.append({
                    "storage_path": e.get("storage_path"),
                    "media_type": e.get("media_type", "image"),
                    "media_role": e.get("media_role", "after"),
                    "is_verified": e.get("is_verified", False)
                })

    has_feedback = any(str(f.get("job_id")) == job_id_str for f in db.feedback.values())
    is_verified = any(str(v.get("job_id")) == job_id_str for v in db.verifications.values())

    return {
        **job,
        "problem_title": problem.get("title", "Repair Job"),
        "problem_description": problem.get("description", ""),
        "customer_name": cust.get("full_name", "Customer"),
        "customer_phone": cust.get("phone"),
        "worker_name": worker_user.get("full_name", "Technician"),
        "worker_phone": worker_user.get("phone"),
        "locality": problem.get("locality"),
        "diagnosis": diagnosis,
        "actions": actions,
        "outcomes": outcomes,
        "evidence": evidence,
        "timeline": timeline_events,
        "has_feedback": has_feedback,
        "is_verified": is_verified
    }

@router.get("/me", response_model=List[JobRead])
def get_my_jobs(
    role: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user)
):
    return list_jobs(role=role, current_user=current_user)

@router.get("", response_model=List[JobRead])
def list_jobs(
    role: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user)
):
    user_id_str = str(current_user.id)
    cust_jobs = [j for j in db.jobs.values() if str(j.get("customer_id")) == user_id_str]
    worker_jobs = []
    if current_user.worker_id:
        worker_id_str = str(current_user.worker_id)
        worker_jobs = [j for j in db.jobs.values() if str(j.get("worker_id")) == worker_id_str]

    if role == "customer":
        jobs = cust_jobs
    elif role == "worker":
        jobs = worker_jobs
    elif current_user.role == "customer":
        jobs = cust_jobs
    elif current_user.role == "worker" and current_user.worker_id:
        seen = set()
        jobs = []
        for j in worker_jobs + cust_jobs:
            jid = str(j.get("id"))
            if jid not in seen:
                seen.add(jid)
                jobs.append(j)
    else:
        jobs = list(db.jobs.values())

    jobs.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)
    return [_hydrate_job(str(j["id"])) for j in jobs]

@router.get("/{job_id}", response_model=JobRead)
def get_job(job_id: uuid.UUID, current_user: CurrentUser = Depends(get_current_user)):
    check_job_participant(str(job_id), current_user)
    return _hydrate_job(str(job_id))

@router.patch("/{job_id}/status", response_model=JobRead)
def update_job_status(
    job_id: uuid.UUID,
    payload: JobStatusUpdate,
    current_user: CurrentUser = Depends(get_current_user)
):
    job_id_str = str(job_id)
    check_job_participant(job_id_str, current_user)
    
    transition_job_status(
        job_id=job_id_str,
        to_status=payload.status,
        changed_by_user_id=str(current_user.id),
        notes=payload.notes
    )

    job = db.jobs[job_id_str]
    # If in_progress, notify customer
    if payload.status == "in_progress":
        send_notification(
            user_id=job.get("customer_id"),
            title="Technician Started Diagnosis",
            message="Your technician has begun on-site inspection/work.",
            notification_type="job_started",
            reference_id=job_id_str
        )

    return _hydrate_job(job_id_str)

@router.post("/{job_id}/completion", response_model=JobRead)
def submit_job_completion(
    job_id: uuid.UUID,
    payload: JobCompletionRequest,
    current_user: CurrentUser = Depends(require_worker)
):
    """
    Technician submits diagnosis, actions, outcomes, and uploaded evidence.
    Creates experience in database and marks job completed.
    """
    job_id_str = str(job_id)
    check_job_worker(job_id_str, current_user)

    actions_dicts = [a.model_dump() for a in payload.actions]
    outcomes_dicts = [o.model_dump() for o in payload.outcomes]
    evidence_dicts = [e.model_dump() for e in payload.evidence]

    record_job_completion(
        job_id=job_id_str,
        worker_user_id=str(current_user.id),
        diagnosis=payload.diagnosis,
        actions=actions_dicts,
        outcomes=outcomes_dicts,
        evidence=evidence_dicts
    )

    job = db.jobs[job_id_str]
    # Notify customer for verification
    send_notification(
        user_id=job.get("customer_id"),
        title="Repair Completed - Verification Required",
        message="Technician submitted completion details. Please review evidence and verify repair.",
        notification_type="verification_required",
        reference_id=job_id_str
    )

    return _hydrate_job(job_id_str)
