import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, status
from backend.config import IST
from backend.api.deps import CurrentUser, get_current_user, require_customer, require_worker
from backend.db.supabase_client import db
from backend.schemas.service_request import (
    ServiceRequestCreate, ServiceRequestUpdate, ServiceRequestRead
)
from backend.services.notifications.notifier import send_notification
from backend.schemas.common import AppException

router = APIRouter(prefix="/service-requests", tags=["Service Requests"])

def _hydrate_request(req_id_str: str) -> dict:
    req = db.service_requests.get(req_id_str)
    if not req:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="RESOURCE_NOT_FOUND",
            message="Service request not found."
        )
    
    problem = db.problems.get(str(req.get("problem_id")), {})
    cust = db.profiles.get(str(problem.get("customer_id")), {})
    worker = db.worker_profiles.get(str(req.get("worker_id")), {})
    worker_user = db.profiles.get(str(worker.get("user_id")), {})
    
    # Check if job was created
    job_id = None
    for j_id, j in db.jobs.items():
        if str(j.get("service_request_id")) == req_id_str:
            job_id = uuid.UUID(j_id)
            break
            
    return {
        **req,
        "problem_title": problem.get("title", "Repair Request"),
        "problem_description": problem.get("description", ""),
        "problem_category": problem.get("category", "General"),
        "customer_name": cust.get("full_name", "Customer"),
        "worker_name": worker_user.get("full_name", "Technician"),
        "locality": problem.get("locality"),
        "created_job_id": job_id
    }

@router.post("", response_model=ServiceRequestRead, status_code=status.HTTP_201_CREATED)
def create_service_request(payload: ServiceRequestCreate, current_user: CurrentUser = Depends(require_customer)):
    prob_str = str(payload.problem_id)
    problem = db.problems.get(prob_str)
    if not problem and db.supabase_client:
        try:
            res_p = db.supabase_client.table("problems").select("*").eq("id", prob_str).execute()
            if res_p.data:
                problem = res_p.data[0]
                db.problems[prob_str] = problem
        except Exception:
            pass

    if not problem:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="RESOURCE_NOT_FOUND",
            message="Problem not found."
        )
    if str(problem.get("customer_id")) != str(current_user.id) and current_user.role != "admin":
        raise AppException(
            status_code=status.HTTP_403_FORBIDDEN,
            code="FORBIDDEN",
            message="You can only request service for your own problem."
        )

    worker_str = str(payload.worker_id)
    worker = db.worker_profiles.get(worker_str)
    if not worker:
        for w in db.worker_profiles.values():
            if str(w.get("user_id")) == worker_str or str(w.get("id")) == worker_str:
                worker = w
                break
    if not worker and db.supabase_client:
        try:
            res_w = db.supabase_client.table("worker_profiles").select("*").or_(f"user_id.eq.{worker_str},id.eq.{worker_str}").execute()
            if res_w.data:
                worker = res_w.data[0]
                db.worker_profiles[worker_str] = worker
        except Exception:
            pass

    if not worker:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="RESOURCE_NOT_FOUND",
            message="Selected technician profile not found."
        )

    # Resolve technician user profile (from cache, fallback to Supabase)
    worker_user_id = str(worker.get("user_id") or worker.get("id") or worker_str)
    worker_user = db.profiles.get(worker_user_id)
    if not worker_user and db.supabase_client:
        try:
            res_u = db.supabase_client.table("profiles").select("*").eq("id", worker_user_id).execute()
            if res_u.data:
                worker_user = res_u.data[0]
                db.profiles[worker_user_id] = worker_user
        except Exception:
            pass

    if not worker_user:
        worker_user = {
            "id": worker_user_id,
            "role": "worker",
            "full_name": worker.get("professional_title") or worker.get("headline") or "Technician",
            "is_active": True
        }
        db.profiles[worker_user_id] = worker_user

    # Verify technician is active if explicit
    if worker_user.get("is_active") is False:
        raise AppException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="VALIDATION_ERROR",
            message="The selected technician account is currently inactive."
        )

    # Optional match_result_id
    match_result_id_val = str(payload.match_result_id) if payload.match_result_id else None

    # Prevent duplicate active requests for the same problem and technician
    for r in db.service_requests.values():
        if (str(r.get("problem_id")) == prob_str and 
            str(r.get("worker_id")) == worker_str and 
            r.get("status") in ["pending", "accepted"]):
            raise AppException(
                status_code=status.HTTP_409_CONFLICT,
                code="CONFLICT",
                message="You already have an active service request with this technician for this problem."
            )

    req_id = str(uuid.uuid4())
    now = datetime.now(IST)
    new_req = {
        "id": req_id,
        "problem_id": prob_str,
        "worker_id": worker_str,
        "match_result_id": str(payload.match_result_id) if payload.match_result_id else None,
        "customer_message": payload.customer_message,
        "worker_response": None,
        "status": "pending",
        "created_at": now,
        "updated_at": now
    }
    db.service_requests[req_id] = new_req
    db.sync_to_supabase("service_requests", new_req)

    # Notify technician
    worker_user_id = worker.get("user_id")
    if worker_user_id:
        notif_id = str(uuid.uuid4())
        db.notifications[notif_id] = {
            "id": notif_id,
            "user_id": str(worker_user_id),
            "notification_type": "request_received",
            "title": "New Service Request",
            "message": f"You received a new service request: {problem.get('title')}",
            "related_entity_type": "service_request",
            "related_entity_id": req_id,
            "is_read": False,
            "created_at": now
        }
        db.sync_to_supabase("notifications", db.notifications[notif_id])

    return _hydrate_request(req_id)

@router.get("/me", response_model=List[ServiceRequestRead])
def get_my_service_requests(
    role: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user)
):
    user_id_str = str(current_user.id)
    cust_problems = {str(p["id"]) for p in db.problems.values() if str(p.get("customer_id")) == user_id_str}
    cust_reqs = [r for r in db.service_requests.values() if str(r.get("problem_id")) in cust_problems]

    worker_reqs = []
    if current_user.worker_id:
        worker_id_str = str(current_user.worker_id)
        worker_reqs = [r for r in db.service_requests.values() if str(r.get("worker_id")) == worker_id_str]

    if role == "customer":
        reqs = cust_reqs
    elif role == "worker":
        reqs = worker_reqs
    elif current_user.role == "customer":
        reqs = cust_reqs
    elif current_user.role == "worker" and current_user.worker_id:
        seen = set()
        reqs = []
        for r in worker_reqs + cust_reqs:
            rid = str(r.get("id"))
            if rid not in seen:
                seen.add(rid)
                reqs.append(r)
    else:
        reqs = []

    reqs.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)
    return [_hydrate_request(str(r["id"])) for r in reqs]

@router.get("", response_model=List[ServiceRequestRead])
def list_service_requests(
    role: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user)
):
    user_id_str = str(current_user.id)
    cust_problems = {str(p["id"]) for p in db.problems.values() if str(p.get("customer_id")) == user_id_str}
    cust_reqs = [r for r in db.service_requests.values() if str(r.get("problem_id")) in cust_problems]

    worker_reqs = []
    if current_user.worker_id:
        worker_id_str = str(current_user.worker_id)
        worker_reqs = [r for r in db.service_requests.values() if str(r.get("worker_id")) == worker_id_str]

    if role == "customer":
        reqs = cust_reqs
    elif role == "worker":
        reqs = worker_reqs
    elif current_user.role == "customer":
        reqs = cust_reqs
    elif current_user.role == "worker" and current_user.worker_id:
        seen = set()
        reqs = []
        for r in worker_reqs + cust_reqs:
            rid = str(r.get("id"))
            if rid not in seen:
                seen.add(rid)
                reqs.append(r)
    else:
        reqs = list(db.service_requests.values())

    reqs.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)
    return [_hydrate_request(str(r["id"])) for r in reqs]

@router.patch("/{request_id}", response_model=ServiceRequestRead)
def update_service_request(
    request_id: uuid.UUID,
    payload: ServiceRequestUpdate,
    current_user: CurrentUser = Depends(require_worker)
):
    req_id_str = str(request_id)
    req = db.service_requests.get(req_id_str)
    if not req:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="RESOURCE_NOT_FOUND",
            message="Service request not found."
        )

    # Verify technician owns this request
    if str(req.get("worker_id")) != str(current_user.worker_id):
        raise AppException(
            status_code=status.HTTP_403_FORBIDDEN,
            code="FORBIDDEN",
            message="You cannot respond to a request assigned to another technician."
        )

    # Verify current request status is PENDING
    current_status = req.get("status", "").lower()
    if current_status != "pending":
        raise AppException(
            status_code=status.HTTP_409_CONFLICT,
            code="CONFLICT",
            message=f"This request has already been processed (current status: {current_status.upper()})."
        )

    status_val = payload.status.lower()
    if status_val not in ["accepted", "rejected", "cancelled"]:
        raise AppException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="VALIDATION_ERROR",
            message="Invalid request status update."
        )

    now = datetime.now(IST)
    req["status"] = status_val
    if payload.worker_response:
        req["worker_response"] = payload.worker_response
    req["updated_at"] = now
    db.sync_to_supabase("service_requests", req)

    problem = db.problems.get(str(req.get("problem_id")), {})
    customer_id = problem.get("customer_id")

    # If ACCEPTED: create exactly one Job in the jobs table
    if status_val == "accepted":
        # Verify job doesn't already exist
        existing_job = None
        for j in db.jobs.values():
            if str(j.get("service_request_id")) == req_id_str:
                existing_job = j
                break
        
        if not existing_job:
            job_id = str(uuid.uuid4())
            new_job = {
                "id": job_id,
                "service_request_id": req_id_str,
                "problem_id": req.get("problem_id"),
                "customer_id": customer_id,
                "worker_id": req.get("worker_id"),
                "experience_id": None,
                "status": "confirmed",
                "notes": payload.worker_response or "Job confirmed by technician.",
                "started_at": None,
                "completed_at": None,
                "created_at": now,
                "updated_at": now
            }
            db.jobs[job_id] = new_job
            db.sync_to_supabase("jobs", new_job)
            
            # Add initial job_status_history
            history_id = str(uuid.uuid4())
            hist_rec = {
                "id": history_id,
                "job_id": job_id,
                "from_status": None,
                "to_status": "confirmed",
                "changed_by": str(current_user.id),
                "notes": "Job confirmed upon service request acceptance",
                "created_at": now
            }
            db.job_status_history[history_id] = hist_rec
            db.sync_to_supabase("job_status_history", hist_rec)

        # Notify customer
        if customer_id:
            send_notification(
                user_id=customer_id,
                title="Service Request Accepted!",
                message="Your service request was accepted by the technician.",
                notification_type="request_accepted",
                reference_id=req_id_str
            )
    elif status_val == "rejected":
        # Notify customer
        if customer_id:
            send_notification(
                user_id=customer_id,
                title="Service Request Declined",
                message="Your service request was declined.",
                notification_type="request_rejected",
                reference_id=req_id_str
            )

    return _hydrate_request(req_id_str)

