import uuid
from typing import Optional
from datetime import datetime
from pydantic import BaseModel

class NotificationRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    message: str
    type: str  # service_request, job_update, verification, etc.
    reference_id: Optional[uuid.UUID] = None
    is_read: bool = False
    created_at: datetime

class NotificationMarkRead(BaseModel):
    is_read: bool = True
