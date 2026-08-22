from sqlalchemy import Column, String, ForeignKey, JSON, Boolean, Text
from sqlalchemy.orm import relationship
from app.models.base_models import BaseModel
from app.models.enums import MessageSenderType

class Conversation(BaseModel):
    __tablename__ = "conversations"

    submission_id: str = Column(String, ForeignKey("submissions.id"), nullable=False)

    # Relationships
    submission = relationship("Submission", backref="conversation")

    def __repr__(self):
        return f"Conversation(id={self.id}, submission_id={self.submission_id})"


class Message(BaseModel):
    __tablename__ = "messages"

    conversation_id: str = Column(String, ForeignKey("conversations.id"), nullable=False)
    sender_type: str = Column(String, nullable=False)  # client, staff, system
    sender_id: str = Column(String, ForeignKey("admins.id"), nullable=True)  # Links to admin table if sender_type is staff
    message: str = Column(Text, nullable=False)
    attachments: list = Column(JSON, nullable=True)  # List of URLs or metadata of uploaded files
    is_read: bool = Column(Boolean, default=False)

    # Relationships
    conversation = relationship("Conversation", backref="messages")
    sender = relationship("Admin", backref="messages_sent")

    def __repr__(self):
        return f"Message(id={self.id}, sender_type={self.sender_type}, is_read={self.is_read})"
