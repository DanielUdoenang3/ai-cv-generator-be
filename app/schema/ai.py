from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import List, Dict, Optional, Any, Union
from datetime import datetime


# ---------------------------------------------------------------------------
# STRUCTURED CV OUTPUT SCHEMAS (Strict Pydantic Models for LLM JSON Response)
# ---------------------------------------------------------------------------

class StructuredCvPersonal(BaseModel):
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin: Optional[str] = None
    portfolio: Optional[str] = None
    target_role: Optional[str] = None


class StructuredCvExperience(BaseModel):
    job_title: str
    company: str
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: bool = False
    bullet_points: List[str] = Field(default_factory=list)


class StructuredCvEducation(BaseModel):
    degree: str
    institution: str
    location: Optional[str] = None
    graduation_year: Optional[str] = None
    honors: Optional[str] = None


class StructuredCvProject(BaseModel):
    title: str
    description: str
    tech_stack: List[str] = Field(default_factory=list)
    link: Optional[str] = None


class StructuredCvCertification(BaseModel):
    """
    Certifications can come back from the LLM as either a plain string
    ("AWS Solutions Architect") or a richer object
    {"name": "...", "issuer": "...", "expiration_date": "..."}.
    Both are normalised into this model.
    """
    name: str
    issuer: Optional[str] = None
    issue_date: Optional[str] = None
    expiration_date: Optional[str] = None

    @classmethod
    def from_raw(cls, value: Union[str, dict]) -> "StructuredCvCertification":
        if isinstance(value, str):
            return cls(name=value)
        if isinstance(value, dict):
            return cls(
                name=value.get("name") or value.get("title") or str(value),
                issuer=value.get("issuer") or value.get("organization"),
                issue_date=value.get("issue_date") or value.get("date"),
                expiration_date=value.get("expiration_date") or value.get("expiry"),
            )
        return cls(name=str(value))


class StructuredCvData(BaseModel):
    personal_info: StructuredCvPersonal
    professional_summary: str
    work_experience: List[StructuredCvExperience] = Field(default_factory=list)
    skills: Dict[str, List[str]] = Field(default_factory=dict)
    education: List[StructuredCvEducation] = Field(default_factory=list)
    projects: List[StructuredCvProject] = Field(default_factory=list)
    certifications: List[StructuredCvCertification] = Field(default_factory=list)

    @field_validator("certifications", mode="before")
    @classmethod
    def coerce_certifications(cls, values: list) -> list:
        """Accept both plain strings and objects from LLM output."""
        return [
            StructuredCvCertification.from_raw(v) if not isinstance(v, StructuredCvCertification) else v
            for v in (values or [])
        ]

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# GENERATION REQUEST & RESPONSE SCHEMAS
# ---------------------------------------------------------------------------

class CvGenerateRequest(BaseModel):
    prompt_id: Optional[str] = Field(None, description="Optional prompt template ID. If omitted, uses active master prompt.")
    provider: str = Field("openai", description="LLM provider: 'openai' or 'gemini'")
    model: Optional[str] = Field(None, description="Specific model name e.g. 'gpt-4o', 'gpt-4o-mini', 'gemini-1.5-flash'")
    custom_instructions: Optional[str] = Field(None, description="Per-generation notes e.g. 'Emphasize 40% latency reduction'")
    include_chat_history: bool = Field(True, description="Whether to include client-admin chat transcript in LLM context")


class AiGenerationLogResponse(BaseModel):
    id: str
    submission_id: str
    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    status: str
    error_message: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CvGenerationResponse(BaseModel):
    ai_generation_id: str
    submission_id: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    cost: float
    status: str
    structured_cv: StructuredCvData

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# PROMPT MANAGEMENT SCHEMAS
# ---------------------------------------------------------------------------

class PromptCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150, description="Friendly title e.g. 'Software Engineer CV'")
    description: Optional[str] = Field(None, description="Subtitle or summary e.g. 'Optimized prompt for software engineering roles'")
    category: Optional[str] = Field(None, description="Role category badge e.g. 'Technology', 'Product', 'Executive', 'Marketing'")
    content: str = Field(..., min_length=10, description="Master system prompt text giving AI instructions")
    is_active: bool = Field(False, description="Set as active prompt for this category")


class PromptUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    description: Optional[str] = Field(None)
    category: Optional[str] = Field(None)
    content: Optional[str] = Field(None, min_length=10)
    is_active: Optional[bool] = None


class PromptResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    content: str
    version: int
    is_active: bool
    usage_count: int = 0
    created_by_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PromptStatsResponse(BaseModel):
    total_prompts: int
    active_prompts: int
    total_usage: int


# ---------------------------------------------------------------------------
# DOCUMENT RENDERING SCHEMAS
# ---------------------------------------------------------------------------

class DocumentRenderRequest(BaseModel):
    ai_generation_id: str = Field(..., description="ID of the AI generation run to render into documents")
    formats: List[str] = Field(
        default=["pdf", "docx"],
        description="List of output formats to render. Supported: 'pdf', 'docx'",
    )


class DocumentResponse(BaseModel):
    id: str
    submission_id: str
    ai_generation_id: Optional[str] = None
    file_name: Optional[str] = None
    file_url: str
    public_id: Optional[str] = None
    file_type: str
    version: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
