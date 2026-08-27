from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base_models import BaseModel
from app.models.enums import TaskPriority, TaskStatus

class Task(BaseModel):
    __tablename__ = "tasks"

    submission_id = Column(String, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    assigned_to_id = Column(String, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    priority = Column(String, default=TaskPriority.NORMAL.value, nullable=False)
    status = Column(String, default=TaskStatus.TODO.value, nullable=False)
    deadline = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    submission = relationship("Submission", backref="tasks")
    assigned_to = relationship("Admin", backref="tasks")

    def __repr__(self):
        return f"Task(id={self.id}, title={self.title}, status={self.status})"
