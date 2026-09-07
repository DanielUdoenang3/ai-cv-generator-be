from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, HttpUrl, field_validator, model_validator

from app.models.enums import (
    DisabilityStatus,
    Gender,
    RaceEthnicity,
    SecurityClearance,
    SexualOrientation,
    VeteranStatus,
    VisaSponsorship,
    WorkArrangement,
)


# ---------------------------------------------------------------------------
# Nested / reusable schemas
# ---------------------------------------------------------------------------


class ProfessionalReference(BaseModel):
    """A single professional reference entry."""

    name: str = Field(..., description="Full name of the reference")
    email: Optional[EmailStr] = Field(None, description="Email address of the reference")
    phone: Optional[str] = Field(None, description="Phone number of the reference")
    company: Optional[str] = Field(None, description="Company or organisation")


# ---------------------------------------------------------------------------
# Legacy structured raw_data sub-schemas (retained for AI context building)
# ---------------------------------------------------------------------------


class EducationSchema(BaseModel):
    institution: str
    degree: str
    field_of_study: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None


class ExperienceSchema(BaseModel):
    company: str
    role: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None


class CertificationSchema(BaseModel):
    name: str
    issuing_organization: Optional[str] = None
    issue_date: Optional[str] = None
    expiration_date: Optional[str] = None


class CVDataSchema(BaseModel):
    """Optional structured breakdown of the candidate's background.

    Kept for backwards compatibility and as supplementary AI context.
    The primary source for AI tailoring is now ``saved_resume_text`` on
    the Submission record.
    """

    education: List[EducationSchema] = Field(default_factory=list)
    experience: List[ExperienceSchema] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    certifications: List[CertificationSchema] = Field(default_factory=list)
    custom_notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Client intake — CREATE
# ---------------------------------------------------------------------------


class CreateSubmission(BaseModel):
    """
    Full client intake form.  Every field the client fills out on their side
    maps 1-to-1 to a column on the ``clients`` or ``submissions`` table.

    Required fields are the absolute minimum needed to create a record.
    All demographic / EEO fields are genuinely optional — never coerce them.
    """

    # ── Core identity ──────────────────────────────────────────────────────
    first_name: str = Field(..., min_length=1, description="Client's first name")
    middle_name: Optional[str] = Field(None, description="Middle name (optional)")
    last_name: str = Field(..., min_length=1, description="Client's last name")
    email: EmailStr = Field(..., description="Email address — used as unique client identifier")
    date_of_birth: Optional[date] = Field(None, description="Date of birth (YYYY-MM-DD)")

    # ── Contact ────────────────────────────────────────────────────────────
    phone: Optional[str] = Field(None, description="Mobile phone number (preferred)")
    address_line: Optional[str] = Field(None, description="Street address or building")
    city: Optional[str] = Field(None, description="City")
    state: Optional[str] = Field(None, description="State or province")
    country: Optional[str] = Field(None, description="Country")
    zip_code: Optional[str] = Field(None, description="ZIP or postal code")

    # ── Online presence ────────────────────────────────────────────────────
    linkedin_url: Optional[str] = Field(None, description="LinkedIn profile URL")
    portfolio_url: Optional[str] = Field(
        None, description="Personal website, GitHub, or portfolio URL"
    )

    # ── Resume file — uploaded separately via /public/upload, URL stored here
    resume_file_url: Optional[str] = Field(
        None, description="Cloudinary URL of the uploaded resume (PDF/DOCX)"
    )
    resume_file_name: Optional[str] = Field(
        None, description="Original filename of the uploaded resume"
    )

    # ── Job preferences ────────────────────────────────────────────────────
    desired_job_titles: Optional[List[str]] = Field(
        None, description="List of desired job titles e.g. ['Product Manager', 'Senior PM']"
    )
    preferred_work_arrangement: Optional[WorkArrangement] = Field(
        None, description="Remote, Hybrid, Onsite, or Flexible"
    )
    expected_salary_range: Optional[str] = Field(
        None, description="Free-text salary expectation e.g. '$120k–$140k'"
    )
    available_start_date: Optional[date] = Field(
        None, description="Date the candidate is available to start (YYYY-MM-DD)"
    )
    companies_to_exclude: Optional[List[str]] = Field(
        None, description="Companies the candidate does NOT want applications sent to"
    )

    # ── Work authorisation ─────────────────────────────────────────────────
    security_clearance: Optional[SecurityClearance] = Field(
        None, description="Active security clearance level if any"
    )
    citizenship_status: Optional[str] = Field(
        None, description="Citizenship or work authorisation status e.g. 'US Citizen', 'EAD'"
    )
    visa_sponsorship_required: Optional[VisaSponsorship] = Field(
        None, description="Whether the candidate requires visa sponsorship"
    )
    non_compete_obligations: Optional[str] = Field(
        None, description="Details of any non-compete or restrictive covenant obligations"
    )

    # ── Professional references ────────────────────────────────────────────
    professional_references: Optional[List[ProfessionalReference]] = Field(
        None, description="Up to N professional references"
    )

    # ── Demographic / EEO (voluntary) ──────────────────────────────────────
    gender: Optional[Gender] = Field(None, description="Gender identity (voluntary)")
    sexual_orientation: Optional[SexualOrientation] = Field(
        None, description="Sexual orientation (voluntary)"
    )
    race_ethnicity: Optional[RaceEthnicity] = Field(
        None, description="Race / ethnicity (voluntary)"
    )
    veteran_status: Optional[VeteranStatus] = Field(
        None, description="Veteran status (voluntary)"
    )
    has_disability: Optional[DisabilityStatus] = Field(
        None, description="Disability status (voluntary)"
    )

    # ── Additional notes ───────────────────────────────────────────────────
    notes: Optional[str] = Field(
        None, description="Any other information the client wants to share"
    )

    # ── Legacy structured CV data (supplementary AI context) ──────────────
    # Still accepted so existing integrations keep working; not required.
    raw_data: Optional[CVDataSchema] = Field(
        None,
        description=(
            "Optional structured breakdown of education, experience, skills "
            "and certifications. Supplementary — the primary AI source is "
            "saved_resume_text on the submission."
        ),
    )

    # ── Submission-level targeting ─────────────────────────────────────────
    target_position: Optional[str] = Field(
        None, description="Role the candidate is targeting with this submission"
    )
    target_company: Optional[str] = Field(None, description="Target company name if known")
    job_description: Optional[str] = Field(
        None, description="Job description the client is applying to (used as primary AI tailoring context)"
    )
    priority: Optional[str] = Field("normal", description="Submission priority: low / normal / high")

    @field_validator("email", mode="before")
    @classmethod
    def normalise_email(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()


# ---------------------------------------------------------------------------
# Submission — UPDATE (saved resume text + job description, by sub-admin)
# ---------------------------------------------------------------------------


class UpdateSavedResumeText(BaseModel):
    """Persist the sub-admin's pasted resume text against the submission.

    This is called once (or whenever the admin wants to update it) so the
    text does not need to be re-pasted on every generation cycle.
    """

    saved_resume_text: str = Field(
        ...,
        min_length=1,
        description="Plain-text resume content to save permanently on this submission",
    )


class UpdateJobDescription(BaseModel):
    """Update the job description for the current tailoring cycle.

    Cleared by the sub-admin clicking DONE at the end of a session.
    """

    job_description: Optional[str] = Field(
        None,
        description="Job description for the current application. Pass null or empty to clear.",
    )


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class ProfessionalReferenceResponse(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None

    model_config = {"from_attributes": True}


class ClientResponse(BaseModel):
    """Full client profile as returned by admin-side endpoints."""

    id: str
    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    email: str
    date_of_birth: Optional[date] = None

    phone: Optional[str] = None
    address_line: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    zip_code: Optional[str] = None

    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None

    resume_file_url: Optional[str] = None
    resume_file_name: Optional[str] = None

    desired_job_titles: Optional[List[str]] = None
    preferred_work_arrangement: Optional[str] = None
    expected_salary_range: Optional[str] = None
    available_start_date: Optional[date] = None
    companies_to_exclude: Optional[List[str]] = None

    security_clearance: Optional[str] = None
    citizenship_status: Optional[str] = None
    visa_sponsorship_required: Optional[str] = None
    non_compete_obligations: Optional[str] = None

    professional_references: Optional[List[ProfessionalReferenceResponse]] = None

    gender: Optional[str] = None
    sexual_orientation: Optional[str] = None
    race_ethnicity: Optional[str] = None
    veteran_status: Optional[str] = None
    has_disability: Optional[str] = None

    notes: Optional[str] = None

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ClientSummaryResponse(BaseModel):
    """Lightweight client profile for list views and submission embeds."""

    id: str
    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    email: str
    phone: Optional[str] = None

    model_config = {"from_attributes": True}


class ActivityLogResponse(BaseModel):
    id: str
    activity_type: str
    title: str
    description: Optional[str] = None
    actor_id: Optional[str] = None
    actor_name: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SubmissionResponse(BaseModel):
    """Full submission record, including embedded client and activity timeline."""

    id: str
    reference_id: str
    client: ClientSummaryResponse
    status: str
    assigned_to_id: Optional[str] = None
    access_token: str

    target_position: Optional[str] = None
    target_company: Optional[str] = None
    priority: str

    job_description: Optional[str] = None
    saved_resume_text: Optional[str] = None
    existing_cv_url: Optional[str] = None
    raw_data: Optional[CVDataSchema] = None

    created_at: datetime
    updated_at: datetime

    activities: List[ActivityLogResponse] = []

    model_config = {"from_attributes": True}


class SubmissionStatusUpdate(BaseModel):
    status: str = Field(..., description="New status value — must be a valid SubmissionStatus")


class SubmissionAssign(BaseModel):
    assigned_to_id: str = Field(..., description="ID of the admin / sub-admin to assign to")
