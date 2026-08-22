from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime

class MessageCreate(BaseModel):
    message: str
    attachments: Optional[List[Any]] = None


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    sender_type: str
    sender_id: Optional[str] = None
    message: str
    attachments: Optional[List[Any]] = None
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    id: str
    submission_id: str
    created_at: datetime
    messages: List[MessageResponse] = []

    class Config:
        from_attributes = True
