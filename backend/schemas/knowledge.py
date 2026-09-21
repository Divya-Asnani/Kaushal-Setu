import uuid
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

class KnowledgeCaseMediaRead(BaseModel):
    id: uuid.UUID
    storage_path: str
    media_type: str = "image"
    caption: Optional[str] = None

class KnowledgeCaseCreate(BaseModel):
    title: str
    problem_summary: str
    diagnosis: str
    solution: str
    lesson_learned: Optional[str] = None
    difficulty: str = "intermediate"
    device_category: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    experience_id: Optional[uuid.UUID] = None
    media_paths: Optional[List[str]] = Field(default_factory=list)

class KnowledgeCaseUpdate(BaseModel):
    title: Optional[str] = None
    problem_summary: Optional[str] = None
    diagnosis: Optional[str] = None
    solution: Optional[str] = None
    lesson_learned: Optional[str] = None
    difficulty: Optional[str] = None
    device_category: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    is_published: Optional[bool] = None

class KnowledgeCaseRead(BaseModel):
    id: uuid.UUID
    worker_id: uuid.UUID
    worker_name: Optional[str] = None
    experience_id: Optional[uuid.UUID] = None
    title: str
    problem_summary: str
    diagnosis: str
    solution: str
    lesson_learned: Optional[str] = None
    difficulty: str = "intermediate"
    device_category: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    is_published: bool = True
    is_verified: bool = False
    view_count: int = 0
    created_at: datetime
    updated_at: datetime
    media: List[KnowledgeCaseMediaRead] = Field(default_factory=list)
