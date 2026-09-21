import uuid
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, status
from backend.config import IST
from backend.api.deps import CurrentUser, get_current_user, require_worker
from backend.db.supabase_client import db
from backend.schemas.experience import ExperienceCreate, ExperienceRead
from backend.schemas.common import AppException

router = APIRouter(prefix="/experiences", tags=["Experiences"])

def _hydrate_experience(exp_id_str: str) -> dict:
    exp = db.experiences.get(exp_id_str)
    if not exp:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="RESOURCE_NOT_FOUND",
            message="Experience not found."
        )

    actions = [a for a in db.experience_actions.values() if str(a.get("experience_id")) == exp_id_str]
    outcomes = [o for o in db.experience_outcomes.values() if str(o.get("experience_id")) == exp_id_str]
    media = [m for m in db.experience_media.values() if str(m.get("experience_id")) == exp_id_str]

    return {
        **exp,
        "actions": sorted(actions, key=lambda x: x.get("step_number", 1)),
        "outcomes": outcomes,
        "media": media
    }

@router.get("/me", response_model=List[ExperienceRead])
def get_my_experiences(current_user: CurrentUser = Depends(require_worker)):
    worker_id_str = str(current_user.worker_id)
    worker_exps = [
        _hydrate_experience(exp_id)
        for exp_id, exp in db.experiences.items()
        if str(exp.get("worker_id")) == worker_id_str
    ]
    worker_exps.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return worker_exps

@router.post("", response_model=ExperienceRead, status_code=status.HTTP_201_CREATED)
def create_experience(
    payload: ExperienceCreate,
    current_user: CurrentUser = Depends(require_worker)
):
    worker_id_str = str(current_user.worker_id)
    exp_id = str(uuid.uuid4())
    now = datetime.now(IST)

    # 1. experiences table
    exp_record = {
        "id": exp_id,
        "worker_id": worker_id_str,
        "title": payload.title,
        "problem_description": payload.problem_description,
        "diagnosis": payload.diagnosis,
        "outcome_summary": payload.outcome_summary or "Repair completed successfully",
        "repair_type": payload.repair_type or "component repair",
        "device_category": payload.device_category or "Electronics",
        "brand": payload.brand,
        "model": payload.model,
        "difficulty": payload.difficulty,
        "experience_status": "submitted",
        "verification_status": "unverified",
        "verification_confidence": 0.0,
        "solved_at": now,
        "created_at": now,
        "updated_at": now
    }
    db.experiences[exp_id] = exp_record
    db.sync_to_supabase("experiences", exp_record)

    # 2. experience_actions table
    for idx, act in enumerate(payload.actions):
        act_id = str(uuid.uuid4())
        act_rec = {
            "id": act_id,
            "experience_id": exp_id,
            "step_number": act.step_number or (idx + 1),
            "action_type": act.action_type,
            "action_description": act.action_description,
            "tools_used": act.tools_used,
            "created_at": now,
            "updated_at": now
        }
        db.experience_actions[act_id] = act_rec
        db.sync_to_supabase("experience_actions", act_rec)

    # 3. experience_outcomes table
    for out in payload.outcomes:
        out_id = str(uuid.uuid4())
        out_rec = {
            "id": out_id,
            "experience_id": exp_id,
            "outcome_type": out.outcome_type,
            "outcome_description": out.outcome_description,
            "success_status": out.success_status,
            "lessons_learned": out.lessons_learned,
            "created_at": now,
            "updated_at": now
        }
        db.experience_outcomes[out_id] = out_rec
        db.sync_to_supabase("experience_outcomes", out_rec)

    # 4. experience_media table
    for med in payload.media:
        med_id = str(uuid.uuid4())
        med_rec = {
            "id": med_id,
            "experience_id": exp_id,
            "storage_path": med.storage_path,
            "media_type": med.media_type,
            "media_role": med.media_role,
            "is_verified": False,
            "created_at": now
        }
        db.experience_media[med_id] = med_rec
        db.sync_to_supabase("experience_media", med_rec)

    # 5. experience_skills table
    for sk_id in payload.skill_ids:
        es_rec = {
            "experience_id": exp_id,
            "skill_id": str(sk_id),
            "proficiency_demonstrated": "advanced",
            "is_primary_skill": True,
            "created_at": now,
            "updated_at": now
        }
        db.experience_skills[f"{exp_id}_{sk_id}"] = es_rec
        db.sync_to_supabase("experience_skills", es_rec)

    return _hydrate_experience(exp_id)

@router.get("/{experience_id}", response_model=ExperienceRead)
def get_experience(experience_id: uuid.UUID, current_user: CurrentUser = Depends(get_current_user)):
    return _hydrate_experience(str(experience_id))
