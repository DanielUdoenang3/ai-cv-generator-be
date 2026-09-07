from sqlalchemy import Column, String, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from app.models.base_models import BaseModel
from app.models.enums import SubmissionStatus


class Submission(BaseModel):
    __tablename__ = "submissions"

    # ── Client link ────────────────────────────────────────────────────────
    client_id: str = Column(String, ForeignKey("clients.id"), nullable=False)

    # ── Tracking ───────────────────────────────────────────────────────────
    reference_id: str = Column(String, unique=True, index=True, nullable=False)
    status: str = Column(String, default=SubmissionStatus.NEW.value, nullable=False)
    assigned_to_id: str = Column(String, ForeignKey("admins.id"), nullable=True)
    access_token: str = Column(String, unique=True, index=True, nullable=False)

    # ── Job targeting (kept for AI context) ───────────────────────────────
    target_position: str = Column(String, nullable=True)
    target_company: str = Column(String, nullable=True)
    priority: str = Column(String, default="normal", nullable=False)

    # ── Raw structured CV data (education / experience / skills / certs) ──
    # Submitted via the intake form as structured JSON arrays.
    raw_data: dict = Column(JSON, nullable=True)

    # ── Uploaded existing CV file (Cloudinary URL, PDF/DOCX) ──────────────
    existing_cv_url: str = Column(String, nullable=True)

    # ── Job description pasted by sub-admin for a specific application ────
    job_description: str = Column(Text, nullable=True)

    # ── Saved resume text ─────────────────────────────────────────────────
    # Plain-text resume the sub-admin pastes once and saves permanently per
    # submission.  Used as the primary source for AI tailoring so it does not
    # need to be re-pasted on every generation cycle.
    saved_resume_text: str = Column(Text, nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────
    client = relationship("Client", backref="submissions")
    assigned_to = relationship("Admin", backref="assigned_submissions")

    def __repr__(self):
        return (
            f"Submission(id={self.id}, reference_id={self.reference_id}, "
            f"status={self.status})"
        )
