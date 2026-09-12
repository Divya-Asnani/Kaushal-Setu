import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status
from backend.config import IST
from backend.api.deps import CurrentUser, require_customer, check_job_customer
from backend.db.supabase_client import db
from backend.schemas.verification import (
    JobVerificationRequest, JobDisputeRequest, VerificationRead
)
from backend.services.jobs.lifecycle import transition_job_status
from backend.services.notifications.notifier import send_notification
from backend.schemas.common import AppException

router = APIRouter(prefix="/jobs", tags=["Verification"])

@router.post("/{job_id}/verify", response_model=VerificationRead)
def verify_completed_job(
    job_id: uuid.UUID,
    payload: JobVerificationRequest,
    current_user: CurrentUser = Depends(require_customer)
):
    """
    Customer verifies completed job.
    Transitions linked experience to 'verified', marking it eligible for intelligent matching confidence.
    """
    job_id_str = str(job_id)
    job = check_job_customer(job_id_str, current_user)

    if job.get("status") != "completed":
        raise AppException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_STATE_TRANSITION",
            message="Only completed jobs can be verified."
        )

    now = datetime.now(IST)
    verif_id = str(uuid.uuid4())
    
    # Check if verification record already exists
    for v_id, v in db.verifications.items():
        if str(v.get("job_id")) == job_id_str:
            verif_id = v_id
            break

    verif_record = {
        "id": verif_id,
        "job_id": job_id_str,
        "customer_id": str(current_user.id),
        "verification_status": "verified",
        "comments": payload.comments,
        "verified_at": now,
        "created_at": now
    }
    db.verifications[verif_id] = verif_record
    db.sync_to_supabase("verifications", verif_record)

    # Transition linked experience to verified
    exp_id_str = str(job.get("experience_id")) if job.get("experience_id") else None
    if exp_id_str and exp_id_str in db.experiences:
        db.experiences[exp_id_str]["verification_status"] = "verified"
        db.experiences[exp_id_str]["updated_at"] = now
        db.sync_to_supabase("experiences", db.experiences[exp_id_str])
        
        # Mark experience media as verified
        for m in db.experience_media.values():
            if str(m.get("experience_id")) == exp_id_str:
                m["is_verified"] = True
                db.sync_to_supabase("experience_media", m)

    # Record in job status history
    h_id = str(uuid.uuid4())
    history_entry = {
        "id": h_id,
        "job_id": job_id_str,
        "from_status": "completed",
        "to_status": "completed",
        "changed_by": str(current_user.id),
        "notes": f"Customer verified job: {payload.comments or 'Confirmed working.'}",
        "created_at": now
    }
    db.job_status_history[h_id] = history_entry
    db.sync_to_supabase("job_status_history", history_entry)

    # Notify technician
    worker = db.worker_profiles.get(str(job.get("worker_id")), {})
    send_notification(
        user_id=worker.get("user_id"),
        title="Job Verification Confirmed!",
        message=f"Customer verified repair. Your experience confidence has been boosted!",
        notification_type="verification_completed",
        reference_id=job_id_str
    )

    return verif_record

@router.post("/{job_id}/dispute", response_model=VerificationRead)
def dispute_completed_job(
    job_id: uuid.UUID,
    payload: JobDisputeRequest,
    current_user: CurrentUser = Depends(require_customer)
):
    """
    Customer disputes completed job.
    Transitions job status to 'disputed' and linked experience to 'disputed'.
    """
    job_id_str = str(job_id)
    job = check_job_customer(job_id_str, current_user)

    if job.get("status") != "completed":
        raise AppException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_STATE_TRANSITION",
            message="Only completed jobs can be disputed."
        )

    now = datetime.now(IST)
    verif_id = str(uuid.uuid4())
    for v_id, v in db.verifications.items():
        if str(v.get("job_id")) == job_id_str:
            verif_id = v_id
            break

    verif_record = {
        "id": verif_id,
        "job_id": job_id_str,
        "customer_id": str(current_user.id),
        "verification_status": "disputed",
        "comments": payload.comments,
        "verified_at": now,
        "created_at": now
    }
    db.verifications[verif_id] = verif_record
    db.sync_to_supabase("verifications", verif_record)

    # Transition job to disputed
    transition_job_status(
        job_id=job_id_str,
        to_status="disputed",
        changed_by_user_id=str(current_user.id),
        notes=f"Customer raised dispute: {payload.comments}"
    )

    # Disputed experience must NOT be treated as verified
    exp_id_str = str(job.get("experience_id")) if job.get("experience_id") else None
    if exp_id_str and exp_id_str in db.experiences:
        db.experiences[exp_id_str]["verification_status"] = "disputed"
        db.experiences[exp_id_str]["updated_at"] = now
        db.sync_to_supabase("experiences", db.experiences[exp_id_str])

    # Notify technician
    worker = db.worker_profiles.get(str(job.get("worker_id")), {})
    send_notification(
        user_id=worker.get("user_id"),
        title="Dispute Raised on Repair Job",
        message=f"Customer reported an issue: {payload.comments}",
        notification_type="job_disputed",
        reference_id=job_id_str
    )

    return verif_record
