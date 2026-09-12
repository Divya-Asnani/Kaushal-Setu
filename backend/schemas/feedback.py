import uuid
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class FeedbackCreate(BaseModel):
    job_id: uuid.UUID
    rating: float = Field(..., ge=1.0, le=5.0)
    feedback_text: Optional[str] = None

class FeedbackRead(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    customer_id: uuid.UUID
    worker_id: uuid.UUID
    rating: float
    feedback_text: Optional[str] = None
    created_at: datetime
