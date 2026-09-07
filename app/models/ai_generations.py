from sqlalchemy import Column, String, Integer, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.models.base_models import BaseModel
from app.models.enums import AiGenerationStatus


class AiGeneration(BaseModel):
    __tablename__ = "ai_generations"

    submission_id = Column(String, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    model = Column(String, nullable=False)
    input_tokens = Column(Integer, default=0, nullable=False)
    output_tokens = Column(Integer, default=0, nullable=False)
    cost = Column(Float, default=0.0, nullable=False)
    status = Column(String, default=AiGenerationStatus.SUCCESS.value, nullable=False)
    error_message = Column(String, nullable=True)

    # Structured resume data — used by the PDF/DOCX resume renderer
    structured_cv_json = Column(JSON, nullable=True)

    # Structured cover letter data — used by the PDF/DOCX cover letter renderer
    cover_letter_json = Column(JSON, nullable=True)

    # Relationships
    submission = relationship("Submission", backref="ai_generations")

    def __repr__(self):
        return f"AiGeneration(id={self.id}, submission_id={self.submission_id}, model={self.model}, status={self.status})"
