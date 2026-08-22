from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from app.schema.submission import ClientResponse

class DashboardStats(BaseModel):
    new_requests: int = Field(..., description="Count of submissions with status 'new'")
    in_progress: int = Field(..., description="Count of submissions with status 'in_progress'")
    completed: int = Field(..., description="Count of submissions with status 'completed'")
    active_chats: int = Field(..., description="Count of active conversations")


class AdminAssignedResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    role: str

    class Config:
        from_attributes = True


class SubmissionRecentResponse(BaseModel):
    id: str
    reference_id: str
    target_position: str
    target_company: Optional[str] = None
    priority: str
    status: str
    created_at: datetime
    updated_at: datetime
    client: Optional[ClientResponse] = None
    assigned_to: Optional[AdminAssignedResponse] = None

    class Config:
        from_attributes = True


class RecentSubmissionsResponse(BaseModel):
    total: int
    page: int
    limit: int
    pages: int
    submissions: List[SubmissionRecentResponse]
