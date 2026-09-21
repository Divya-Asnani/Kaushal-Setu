import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status
from backend.config import IST
from backend.api.deps import CurrentUser, get_current_user
from backend.db.supabase_client import db
from backend.schemas.profile import ProfileRead, ProfileUpdate, BecomeWorkerRequest
from backend.schemas.common import AppException

router = APIRouter(tags=["Profile"])

@router.get("/me", response_model=ProfileRead)
def get_my_profile(current_user: CurrentUser = Depends(get_current_user)):
    profile = db.profiles.get(str(current_user.id))
    if not profile:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="RESOURCE_NOT_FOUND",
            message="Profile not found."
        )
    return profile

@router.patch("/me", response_model=ProfileRead)
def update_my_profile(payload: ProfileUpdate, current_user: CurrentUser = Depends(get_current_user)):
    profile = db.profiles.get(str(current_user.id))
    if not profile:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="RESOURCE_NOT_FOUND",
            message="Profile not found."
        )
    
    update_data = payload.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        if val is not None:
            profile[key] = val
    profile["updated_at"] = datetime.now(IST)
    db.sync_to_supabase("profiles", profile)

    # If user also has a worker_profile, sync locality & city there too
    user_id_str = str(current_user.id)
    for wp in db.worker_profiles.values():
        if str(wp.get("user_id")) == user_id_str:
            if "locality" in update_data and update_data["locality"] is not None:
                wp["locality"] = update_data["locality"]
            if "city" in update_data and update_data["city"] is not None:
                wp["city"] = update_data["city"]
            wp["updated_at"] = datetime.now(IST)
            db.sync_to_supabase("worker_profiles", wp)
            break

    return profile

@router.post("/become-worker", response_model=ProfileRead)
@router.post("/profile/become-worker", response_model=ProfileRead)
def become_worker(
    payload: BecomeWorkerRequest,
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    In-app technician onboarding (Uber-style). Upgrades current user's profile to 'worker'
    and provisions a matching worker_profiles record in Supabase PostgreSQL.
    """
    user_id_str = str(current_user.id)
    profile = db.profiles.get(user_id_str)
    if not profile:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="RESOURCE_NOT_FOUND",
            message="Profile not found."
        )

    now = datetime.now(IST)
    # 1. Update profiles role to worker
    profile["role"] = "worker"
    profile["updated_at"] = now
    db.profiles[user_id_str] = profile
    db.sync_to_supabase("profiles", profile)

    # 2. Provision or update worker_profiles
    existing_worker = db.worker_profiles.get(user_id_str)
    worker_record = {
        "id": user_id_str,
        "user_id": user_id_str,
        "service_category": payload.service_category,
        "headline": payload.headline or f"Certified {payload.service_category.title()} Specialist",
        "professional_title": payload.headline or f"Certified {payload.service_category.title()} Specialist",
        "bio": payload.bio or "Certified technician on KaushalSetu.",
        "experience_years": payload.experience_years,
        "years_experience": payload.experience_years,
        "hourly_rate": payload.hourly_rate,
        "service_radius_km": payload.service_radius_km,
        "latitude": 19.0760,
        "longitude": 72.8777,
        "locality": payload.locality or profile.get("locality"),
        "city": payload.city or profile.get("city"),
        "state": "Maharashtra",
        "postal_code": "400050",
        "is_available": True,
        "availability_status": "available",
        "is_verified": existing_worker.get("is_verified", False) if existing_worker else False,
        "rating": existing_worker.get("rating", 5.0) if existing_worker else 5.0,
        "total_reviews": existing_worker.get("total_reviews", 0) if existing_worker else 0,
        "created_at": existing_worker["created_at"] if existing_worker else now,
        "updated_at": now
    }
    db.worker_profiles[user_id_str] = worker_record
    db.sync_to_supabase("worker_profiles", worker_record)

    # 3. Auto-provision initial matching skills if new technician has no skills yet
    existing_skills = [s for s in db.worker_skills.values() if str(s.get("worker_id")) == user_id_str]
    if not existing_skills:
        cat_lower = (payload.service_category or "electronics").lower()
        matched_skills = [
            s for s in db.skills.values()
            if cat_lower in str(s.get("category", "")).lower() or cat_lower in str(s.get("name", "")).lower()
        ]
        if not matched_skills:
            matched_skills = list(db.skills.values())[:2]
        
        for sk in matched_skills[:3]:
            new_sk_id = str(uuid.uuid4())
            sk_rec = {
                "id": new_sk_id,
                "worker_id": user_id_str,
                "skill_id": str(sk["id"]),
                "proficiency_level": "expert" if payload.experience_years >= 5 else "intermediate",
                "verified": False,
                "created_at": now
            }
            db.worker_skills[new_sk_id] = sk_rec
            db.sync_to_supabase("worker_skills", sk_rec)

    return profile

