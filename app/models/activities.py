from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.models.base_models import BaseModel


class SubmissionActivity(BaseModel):
    __tablename__ = "submission_activities"

    submission_id: str = Column(
        String, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False
    )
    activity_type: str = Column(String, nullable=False)  # e.g., 'submission_created', 'assigned', 'status_changed'
    title: str = Column(String, nullable=False)
    description: str = Column(String, nullable=True)
    actor_id: str = Column(
        String, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    submission = relationship("Submission", backref="activities")
    actor = relationship("Admin")

    def __repr__(self):
        return f"SubmissionActivity(id={self.id}, type={self.activity_type}, title={self.title})"
