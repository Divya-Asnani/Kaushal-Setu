import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class ExperienceActionRead(BaseModel):
    id: uuid.UUID
    step_number: int
    action_type: str
    action_description: str
    tools_used: List[str] = Field(default_factory=list)

class ExperienceOutcomeRead(BaseModel):
    id: uuid.UUID
    outcome_type: str
    outcome_description: str
    success_status: str
    lessons_learned: Optional[str] = None

class ExperienceMediaRead(BaseModel):
    id: uuid.UUID
    storage_path: str
    media_type: str
    media_role: str
    is_verified: bool

class ExperienceActionCreate(BaseModel):
    step_number: int = 1
    action_type: str = "repair"
    action_description: str
    tools_used: List[str] = Field(default_factory=list)

class ExperienceOutcomeCreate(BaseModel):
    outcome_type: str = "repair_result"
    outcome_description: str
    success_status: str = "successful"
    lessons_learned: Optional[str] = None

class ExperienceMediaCreate(BaseModel):
    storage_path: str
    media_type: str = "image"
    media_role: str = "after"

class ExperienceCreate(BaseModel):
    title: str
    problem_description: str
    diagnosis: str
    outcome_summary: Optional[str] = "Repair completed successfully"
    repair_type: Optional[str] = None
    device_category: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    difficulty: str = "intermediate"
    actions: List[ExperienceActionCreate] = Field(default_factory=list)
    outcomes: List[ExperienceOutcomeCreate] = Field(default_factory=list)
    media: List[ExperienceMediaCreate] = Field(default_factory=list)
    skill_ids: List[uuid.UUID] = Field(default_factory=list)

class ExperienceRead(BaseModel):
    id: uuid.UUID
    worker_id: uuid.UUID
    title: str
    problem_description: Optional[str] = None
    diagnosis: str
    outcome_summary: Optional[str] = None
    repair_type: Optional[str] = None
    device_category: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    difficulty: str = "intermediate"
    verification_status: str = "unverified"
    created_at: datetime
    actions: List[ExperienceActionRead] = Field(default_factory=list)
    outcomes: List[ExperienceOutcomeRead] = Field(default_factory=list)
    media: List[ExperienceMediaRead] = Field(default_factory=list)
