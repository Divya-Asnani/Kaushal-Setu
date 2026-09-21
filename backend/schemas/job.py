import uuid
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

class JobStatusUpdate(BaseModel):
    status: str  # in_progress, cancelled, etc.
    notes: Optional[str] = None

class JobActionItem(BaseModel):
    step_number: int
    action_type: str  # diagnostic, repair, replacement, test
    action_description: str
    tools_used: List[str] = Field(default_factory=list)

class JobOutcomeItem(BaseModel):
    outcome_type: str  # repair_result, performance_test, functional_check
    outcome_description: str
    success_status: str = "successful"  # successful, partial, unsuccessful
    lessons_learned: Optional[str] = None

class JobEvidenceItem(BaseModel):
    storage_path: str
    media_type: str = "image"
    media_role: str = "after"  # before, during, after, diagnostic
    is_verified: bool = False

class JobCompletionRequest(BaseModel):
    diagnosis: str
    actions: List[JobActionItem] = Field(default_factory=list)
    outcomes: List[JobOutcomeItem] = Field(default_factory=list)
    evidence: List[JobEvidenceItem] = Field(default_factory=list)

class JobTimelineEvent(BaseModel):
    id: uuid.UUID
    from_status: Optional[str] = None
    to_status: str
    changed_by_name: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

class JobRead(BaseModel):
    id: uuid.UUID
    service_request_id: uuid.UUID
    problem_id: uuid.UUID
    customer_id: uuid.UUID
    worker_id: uuid.UUID
    experience_id: Optional[uuid.UUID] = None
    status: str
    notes: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    # Detail metadata
    problem_title: Optional[str] = None
    problem_description: Optional[str] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    worker_name: Optional[str] = None
    worker_phone: Optional[str] = None
    locality: Optional[str] = None
    
    # Completion details if submitted
    diagnosis: Optional[str] = None
    actions: List[JobActionItem] = Field(default_factory=list)
    outcomes: List[JobOutcomeItem] = Field(default_factory=list)
    evidence: List[JobEvidenceItem] = Field(default_factory=list)
    timeline: List[JobTimelineEvent] = Field(default_factory=list)
    has_feedback: bool = False
    is_verified: bool = False
