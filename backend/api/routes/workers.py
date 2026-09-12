import uuid
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, status
from backend.config import IST
from backend.api.deps import CurrentUser, get_current_user, require_worker
from backend.db.supabase_client import db
from backend.schemas.worker import (
    WorkerProfileRead, WorkerProfileUpdate,
    WorkerSkillCreate, WorkerSkillRead,
    CertificateCreate, CertificateRead, SkillRead
)
from backend.schemas.experience import ExperienceRead
from backend.schemas.common import AppException

router = APIRouter(prefix="/workers", tags=["Workers"])

def _hydrate_worker_profile(worker_id_str: str) -> dict:
    worker = db.worker_profiles.get(worker_id_str)
    if not worker:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="RESOURCE_NOT_FOUND",
            message="Worker profile not found."
        )
    
    user_id_str = str(worker.get("user_id"))
    profile = db.profiles.get(user_id_str, {})
    
    # Hydrate skills
    skills_list = []
    for ws in db.worker_skills.values():
        if str(ws.get("worker_id")) == worker_id_str:
            sk = db.skills.get(str(ws.get("skill_id")), {})
            raw_id = ws.get("id")
            try:
                valid_id = uuid.UUID(str(raw_id))
            except Exception:
                valid_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"{worker_id_str}_{ws.get('skill_id')}")
            skills_list.append({
                "id": valid_id,
                "skill_id": ws["skill_id"],
                "skill_name": sk.get("name", "Unknown"),
                "category": sk.get("category", "General"),
                "proficiency_level": ws.get("proficiency_level", "intermediate"),
                "verified": ws.get("verified", False)
            })

    # Hydrate certificates
    certs_list = []
    for cert in db.certificates.values():
        if str(cert.get("worker_id")) == worker_id_str:
            certs_list.append({
                "id": cert.get("id") or str(uuid.uuid4()),
                "worker_id": cert.get("worker_id"),
                "title": cert.get("title") or cert.get("certificate_name") or "Certificate",
                "issuing_organization": cert.get("issuing_organization") or "Organization",
                "issue_date": cert.get("issue_date"),
                "expiry_date": cert.get("expiry_date"),
                "credential_url": cert.get("credential_url") or cert.get("certificate_url"),
                "storage_path": cert.get("storage_path"),
                "is_verified": cert.get("is_verified", False) or (cert.get("verification_status") == "verified"),
                "created_at": cert.get("created_at") or datetime.now(IST)
            })

    # Calculate aggregate rating directly from real feedback records
    all_ratings = [
        f.get("rating") for f in db.feedback.values()
        if str(f.get("worker_id")) == worker_id_str and f.get("rating") is not None
    ]
    avg_rating = round(sum(all_ratings) / len(all_ratings), 2) if all_ratings else float(worker.get("rating") or 5.0)
    total_reviews = len(all_ratings) if all_ratings else int(worker.get("total_reviews") or 0)

    return {
        **worker,
        "rating": avg_rating,
        "total_reviews": total_reviews,
        "full_name": profile.get("full_name", "Technician"),
        "email": profile.get("email", ""),
        "phone": profile.get("phone"),
        "skills": skills_list,
        "certificates": certs_list
    }

@router.get("/me", response_model=WorkerProfileRead)
def get_my_worker_profile(current_user: CurrentUser = Depends(require_worker)):
    return _hydrate_worker_profile(str(current_user.worker_id))

@router.patch("/me", response_model=WorkerProfileRead)
def update_my_worker_profile(payload: WorkerProfileUpdate, current_user: CurrentUser = Depends(require_worker)):
    worker = db.worker_profiles.get(str(current_user.worker_id))
    if not worker:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="RESOURCE_NOT_FOUND",
            message="Worker profile not found."
        )
    
    update_data = payload.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        if val is not None:
            worker[key] = val
    worker["updated_at"] = datetime.now(IST)
    db.sync_to_supabase("worker_profiles", worker)
    return _hydrate_worker_profile(str(current_user.worker_id))

@router.put("/me/skills", response_model=List[WorkerSkillRead])
def update_my_skills(skills_in: List[WorkerSkillCreate], current_user: CurrentUser = Depends(require_worker)):
    worker_id_str = str(current_user.worker_id)
    
    # Remove existing skills
    keys_to_remove = [k for k, v in db.worker_skills.items() if str(v.get("worker_id")) == worker_id_str]
    for k in keys_to_remove:
        del db.worker_skills[k]
        
    if db.supabase_client:
        try:
            db.supabase_client.table("worker_skills").delete().eq("worker_id", worker_id_str).execute()
        except Exception:
            pass

    now = datetime.now(IST)
    for s_in in skills_in:
        new_id = str(uuid.uuid4())
        ws_record = {
            "id": new_id,
            "worker_id": worker_id_str,
            "skill_id": str(s_in.skill_id),
            "proficiency_level": s_in.proficiency_level,
            "verified": False,
            "created_at": now
        }
        db.worker_skills[new_id] = ws_record
        db.sync_to_supabase("worker_skills", ws_record)
        
    hydrated = _hydrate_worker_profile(worker_id_str)
    return hydrated["skills"]

@router.post("/me/certificates", response_model=CertificateRead, status_code=status.HTTP_201_CREATED)
def add_certificate(cert_in: CertificateCreate, current_user: CurrentUser = Depends(require_worker)):
    worker_id_str = str(current_user.worker_id)
    cert_id = str(uuid.uuid4())
    now = datetime.now(IST)
    new_cert = {
        "id": cert_id,
        "worker_id": worker_id_str,
        "title": cert_in.title,
        "certificate_name": cert_in.title,
        "issuing_organization": cert_in.issuing_organization,
        "issue_date": cert_in.issue_date.isoformat() if cert_in.issue_date else None,
        "expiry_date": cert_in.expiry_date.isoformat() if cert_in.expiry_date else None,
        "credential_url": cert_in.credential_url,
        "certificate_url": cert_in.credential_url,
        "storage_path": cert_in.storage_path,
        "is_verified": False,
        "verification_status": "pending",
        "created_at": now
    }
    db.certificates[cert_id] = new_cert
    db.sync_to_supabase("certificates", new_cert)
    return {
        "id": cert_id,
        "worker_id": worker_id_str,
        "title": cert_in.title,
        "issuing_organization": cert_in.issuing_organization,
        "issue_date": cert_in.issue_date,
        "expiry_date": cert_in.expiry_date,
        "credential_url": cert_in.credential_url,
        "storage_path": cert_in.storage_path,
        "is_verified": False,
        "created_at": now
    }

@router.get("/{worker_id}", response_model=WorkerProfileRead)
def get_worker_by_id(worker_id: uuid.UUID, current_user: CurrentUser = Depends(get_current_user)):
    return _hydrate_worker_profile(str(worker_id))

@router.get("/{worker_id}/experiences", response_model=List[ExperienceRead])
def get_worker_experiences(worker_id: uuid.UUID, current_user: CurrentUser = Depends(get_current_user)):
    worker_id_str = str(worker_id)
    worker_exps = []
    for exp_id, exp in db.experiences.items():
        if str(exp.get("worker_id")) == worker_id_str:
            actions = [a for a in db.experience_actions.values() if str(a.get("experience_id")) == exp_id]
            outcomes = [o for o in db.experience_outcomes.values() if str(o.get("experience_id")) == exp_id]
            media = [m for m in db.experience_media.values() if str(m.get("experience_id")) == exp_id]
            worker_exps.append({
                **exp,
                "actions": sorted(actions, key=lambda x: x.get("step_number", 1)),
                "outcomes": outcomes,
                "media": media
            })
    return worker_exps
