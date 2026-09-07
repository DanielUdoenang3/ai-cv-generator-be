from sqlalchemy import Column, String, Date, Boolean, JSON, Text
from app.models.base_models import BaseModel


class Client(BaseModel):
    __tablename__ = "clients"

    # ── Core identity ──────────────────────────────────────────────────────
    first_name: str = Column(String, nullable=False)
    middle_name: str = Column(String, nullable=True)
    last_name: str = Column(String, nullable=False)
    email: str = Column(String, unique=True, index=True, nullable=False)
    date_of_birth = Column(Date, nullable=True)

    # ── Contact ────────────────────────────────────────────────────────────
    phone: str = Column(String, nullable=True)          # Mobile preferred
    address_line: str = Column(String, nullable=True)   # Street / building
    city: str = Column(String, nullable=True)
    state: str = Column(String, nullable=True)
    country: str = Column(String, nullable=True)
    zip_code: str = Column(String, nullable=True)

    # ── Online presence ────────────────────────────────────────────────────
    linkedin_url: str = Column(String, nullable=True)
    portfolio_url: str = Column(String, nullable=True)  # GitHub, personal site, etc.

    # ── Resume file (Cloudinary URL, PDF/DOCX only) ────────────────────────
    resume_file_url: str = Column(String, nullable=True)
    resume_file_name: str = Column(String, nullable=True)

    # ── Job preferences ────────────────────────────────────────────────────
    desired_job_titles: list = Column(JSON, nullable=True)          # ["Product Manager", "Senior PM"]
    preferred_work_arrangement: str = Column(String, nullable=True)  # WorkArrangement enum value
    expected_salary_range: str = Column(String, nullable=True)       # Free text e.g. "$120k–$140k"
    available_start_date = Column(Date, nullable=True)
    companies_to_exclude: list = Column(JSON, nullable=True)         # ["Amazon", "Google"]

    # ── Work authorisation ─────────────────────────────────────────────────
    security_clearance: str = Column(String, nullable=True)          # SecurityClearance enum value
    citizenship_status: str = Column(String, nullable=True)          # Free text e.g. "US Citizen"
    visa_sponsorship_required: str = Column(String, nullable=True)   # VisaSponsorship enum value
    non_compete_obligations: str = Column(Text, nullable=True)       # Free text description

    # ── Professional references (list of {name, email, phone, company}) ───
    professional_references: list = Column(JSON, nullable=True)

    # ── Demographic (voluntary / EEO) ─────────────────────────────────────
    gender: str = Column(String, nullable=True)              # Gender enum value
    sexual_orientation: str = Column(String, nullable=True)  # SexualOrientation enum value
    race_ethnicity: str = Column(String, nullable=True)      # RaceEthnicity enum value
    veteran_status: str = Column(String, nullable=True)      # VeteranStatus enum value
    has_disability: str = Column(String, nullable=True)      # DisabilityStatus enum value

    # ── Additional notes ───────────────────────────────────────────────────
    notes: str = Column(Text, nullable=True)

    def __repr__(self):
        return (
            f"Client(id={self.id}, name={self.first_name} {self.last_name}, "
            f"email={self.email})"
        )
