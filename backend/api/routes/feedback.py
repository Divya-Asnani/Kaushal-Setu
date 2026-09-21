import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status
from backend.config import IST
from backend.api.deps import CurrentUser, require_customer, check_job_customer
from backend.db.supabase_client import db
from backend.schemas.feedback import FeedbackCreate, FeedbackRead
from backend.schemas.common import AppException

router = APIRouter(prefix="/feedback", tags=["Feedback"])

@router.post("", response_model=FeedbackRead, status_code=status.HTTP_201_CREATED)
def submit_feedback(payload: FeedbackCreate, current_user: CurrentUser = Depends(require_customer)):
    job_id_str = str(payload.job_id)
    job = check_job_customer(job_id_str, current_user)

    if job.get("status") != "completed":
        raise AppException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_STATE_TRANSITION",
            message="Feedback can only be submitted for completed jobs."
        )

    # Check for existing duplicate feedback on this job
    for fb in db.feedback.values():
        if str(fb.get("job_id")) == job_id_str:
            raise AppException(
                status_code=status.HTTP_409_CONFLICT,
                code="CONFLICT",
                message="You have already reviewed this job."
            )

    now = datetime.now(IST)
    fb_id = str(uuid.uuid4())
    worker_id_str = str(job.get("worker_id"))

    new_fb = {
        "id": fb_id,
        "job_id": job_id_str,
        "customer_id": str(current_user.id),
        "worker_id": worker_id_str,
        "rating": round(payload.rating, 1),
        "feedback_text": payload.feedback_text,
        "created_at": now
    }
    db.feedback[fb_id] = new_fb
    db.sync_to_supabase("feedback", new_fb)

    # Update technician average rating in worker_profiles
    worker = db.worker_profiles.get(worker_id_str)
    if worker:
        all_ratings = [
            f.get("rating") for f in db.feedback.values()
            if str(f.get("worker_id")) == worker_id_str
        ]
        if all_ratings:
            worker["rating"] = round(sum(all_ratings) / len(all_ratings), 2)
            worker["total_reviews"] = len(all_ratings)
            worker["updated_at"] = now
            db.sync_to_supabase("worker_profiles", worker)

    return new_fb
