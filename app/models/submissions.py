from sqlalchemy import Column, String, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.models.base_models import BaseModel
from app.models.enums import SubmissionStatus

class Submission(BaseModel):
    __tablename__ = "submissions"

    client_id: str = Column(String, ForeignKey("clients.id"), nullable=False)
    reference_id: str = Column(String, unique=True, index=True, nullable=False)
    target_position: str = Column(String, nullable=False)
    target_company: str = Column(String, nullable=True)
    priority: str = Column(String, default="normal", nullable=False)
    job_description: str = Column(String, nullable=True)
    raw_data: dict = Column(JSON, nullable=True)  # stores education, experience, skills, certifications, etc.
    status: str = Column(String, default=SubmissionStatus.NEW.value, nullable=False)
    assigned_to_id: str = Column(String, ForeignKey("admins.id"), nullable=True)
    access_token: str = Column(String, unique=True, index=True, nullable=False)
    existing_cv_url: str = Column(String, nullable=True)  # URL of uploaded existing CV on Cloudinary

    # Relationships
    client = relationship("Client", backref="submissions")
    assigned_to = relationship("Admin", backref="assigned_submissions")

    def __repr__(self):
        return f"Submission(id={self.id}, target_position={self.target_position}, status={self.status})"
