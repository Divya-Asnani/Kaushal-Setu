import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class ProblemCreate(BaseModel):
    title: str
    description: str
    address_line: Optional[str] = None
    locality: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    latitude: float
    longitude: float
    media_paths: Optional[List[str]] = Field(default_factory=list)

class ProblemMediaRead(BaseModel):
    id: uuid.UUID
    problem_id: uuid.UUID
    storage_path: str
    media_type: str = "image"
    created_at: datetime

class ProblemFingerprintRequest(BaseModel):
    regenerate: bool = False

class ProblemFingerprintRead(BaseModel):
    id: uuid.UUID
    problem_id: uuid.UUID
    device_type: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    category: Optional[str] = None
    issue: Optional[str] = None
    symptoms: List[str] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    suspected_component: Optional[str] = None
    repair_type: Optional[str] = None
    extracted_skills: List[str] = Field(default_factory=list)
    ai_summary: Optional[str] = None
    fingerprint_version: int = 1
    embedding_status: str = "completed"
    created_at: datetime

class ProblemRead(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    title: str
    description: str
    address_line: Optional[str] = None
    locality: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    latitude: float
    longitude: float
    status: str = "open"
    created_at: datetime
    updated_at: datetime
    media: List[ProblemMediaRead] = Field(default_factory=list)
    fingerprint: Optional[ProblemFingerprintRead] = None
