from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base_models import BaseModel
from app.models.enums import DocumentType


class Document(BaseModel):
    __tablename__ = "documents"

    submission_id = Column(String, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    ai_generation_id = Column(String, ForeignKey("ai_generations.id", ondelete="SET NULL"), nullable=True)
    file_url = Column(String, nullable=False)
    file_name = Column(String, nullable=True)
    public_id = Column(String, nullable=True)  # Cloudinary public_id for management
    file_type = Column(String, default=DocumentType.PDF.value, nullable=False)
    version = Column(Integer, default=1, nullable=False)

    # Relationships
    submission = relationship("Submission", backref="documents")
    ai_generation = relationship("AiGeneration", backref="documents")

    def __repr__(self):
        return f"Document(id={self.id}, submission_id={self.submission_id}, file_type={self.file_type}, version={self.version})"
