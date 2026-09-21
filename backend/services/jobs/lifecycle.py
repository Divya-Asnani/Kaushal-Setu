import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import status
from backend.config import IST
from backend.db.supabase_client import db
from backend.schemas.common import AppException

# Valid state machine transitions (Section 11)
ALLOWED_TRANSITIONS = {
    "confirmed": ["in_progress", "cancelled"],
    "in_progress": ["completed", "cancelled"],
    "completed": ["disputed"],
    "cancelled": [],
    "disputed": ["completed"]
}

def transition_job_status(
    job_id: str,
    to_status: str,
    changed_by_user_id: str,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    job = db.jobs.get(str(job_id))
    if not job:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="RESOURCE_NOT_FOUND",
            message="Job not found."
        )

    current_status = job.get("status")
    allowed = ALLOWED_TRANSITIONS.get(current_status, [])

    if to_status not in allowed and to_status != current_status:
        raise AppException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_STATE_TRANSITION",
            message=f"Cannot transition job from '{current_status}' to '{to_status}'. Allowed: {allowed}."
        )

    now = datetime.now(IST)
    from_status = current_status
    job["status"] = to_status
    job["updated_at"] = now
    if notes:
        job["notes"] = notes

    if to_status == "in_progress" and not job.get("started_at"):
        job["started_at"] = now
    elif to_status == "completed" and not job.get("completed_at"):
        job["completed_at"] = now

    # Record job_status_history atomically (Section 11)
    history_id = str(uuid.uuid4())
    history_entry = {
        "id": history_id,
        "job_id": str(job_id),
        "from_status": from_status,
        "to_status": to_status,
        "changed_by": str(changed_by_user_id),
        "notes": notes,
        "created_at": now
    }
    db.job_status_history[history_id] = history_entry

    db.sync_to_supabase("jobs", job)
    db.sync_to_supabase("job_status_history", history_entry)

    return job

def record_job_completion(
    job_id: str,
    worker_user_id: str,
    diagnosis: str,
    actions: List[Dict[str, Any]],
    outcomes: List[Dict[str, Any]],
    evidence: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Submits job completion:
    Creates experience record, actions, outcomes, and media; transitions job to completed.
    Completion does NOT automatically mean customer verified (Section 12 & 13).
    """
    job = db.jobs.get(str(job_id))
    if not job:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="RESOURCE_NOT_FOUND",
            message="Job not found."
        )

    now = datetime.now(IST)
    worker_id = job.get("worker_id")
    problem = db.problems.get(str(job.get("problem_id")), {})
    fingerprint = db.problem_fingerprints.get(str(job.get("problem_id")), {})

    # 1. Create Experience (experiences table)
    exp_id = str(uuid.uuid4())
    db.experiences[exp_id] = {
        "id": exp_id,
        "worker_id": worker_id,
        "title": f"Repair of {problem.get('title', 'Equipment')}",
        "problem_description": problem.get('description', diagnosis),
        "diagnosis": diagnosis,
        "outcome_summary": "Repair completed and verified successfully",
        "experience_status": "submitted",
        "verification_confidence": 0.0,
        "solved_at": now,
        "created_at": now,
        "updated_at": now
    }
    db.sync_to_supabase("experiences", db.experiences[exp_id])

    # 2. Add experience_actions
    for act in actions:
        act_id = str(uuid.uuid4())
        act_entry = {
            "id": act_id,
            "experience_id": exp_id,
            "step_number": act.get("step_number", 1),
            "action_type": act.get("action_type", "repair"),
            "action_description": act.get("action_description", ""),
            "tools_used": act.get("tools_used", []),
            "created_at": now,
            "updated_at": now
        }
        db.experience_actions[act_id] = act_entry
        db.sync_to_supabase("experience_actions", act_entry)

    # 3. Add experience_outcomes
    for out in outcomes:
        out_id = str(uuid.uuid4())
        out_entry = {
            "id": out_id,
            "experience_id": exp_id,
            "outcome_type": out.get("outcome_type", "repair_result"),
            "outcome_description": out.get("outcome_description", ""),
            "success_status": out.get("success_status", "successful"),
            "created_at": now,
            "updated_at": now
        }
        db.experience_outcomes[out_id] = out_entry
        db.sync_to_supabase("experience_outcomes", out_entry)

    # 4. Add experience_media (Section 13)
    for ev in evidence:
        ev_id = str(uuid.uuid4())
        media_entry = {
            "id": ev_id,
            "experience_id": exp_id,
            "storage_path": ev.get("storage_path"),
            "media_type": ev.get("media_type", "image"),
            "media_role": ev.get("media_role", "after"),
            "is_verified": False,
            "created_at": now
        }
        db.experience_media[ev_id] = media_entry
        db.sync_to_supabase("experience_media", media_entry)

    # 5. Link experience to job and transition to completed
    job["experience_id"] = exp_id
    transition_job_status(
        job_id=job_id,
        to_status="completed",
        changed_by_user_id=worker_user_id,
        notes=f"Work completed with diagnosis: {diagnosis}"
    )

    return job
