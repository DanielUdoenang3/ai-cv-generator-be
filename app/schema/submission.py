from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime

class EducationSchema(BaseModel):
    institution: str
    degree: str
    field_of_study: Optional[str] = None
    start_date: str
    end_date: Optional[str] = None
    description: Optional[str] = None


class ExperienceSchema(BaseModel):
    company: str
    role: str
    start_date: str
    end_date: Optional[str] = None
    description: Optional[str] = None


class CertificationSchema(BaseModel):
    name: str
    issuing_organization: str
    issue_date: Optional[str] = None
    expiration_date: Optional[str] = None


class CVDataSchema(BaseModel):
    education: List[EducationSchema] = Field(default_factory=list)
    experience: List[ExperienceSchema] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    certifications: List[CertificationSchema] = Field(default_factory=list)
    custom_notes: Optional[str] = None


class CreateSubmission(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    target_position: str
    target_company: Optional[str] = None
    priority: Optional[str] = "normal"
    job_description: Optional[str] = None
    existing_cv_url: Optional[str] = None
    raw_data: CVDataSchema


class ClientResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None

    class Config:
        from_attributes = True


class ActivityLogResponse(BaseModel):
    id: str
    activity_type: str
    title: str
    description: Optional[str] = None
    actor_id: Optional[str] = None
    actor_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SubmissionResponse(BaseModel):
    id: str
    reference_id: str
    client: ClientResponse
    target_position: str
    target_company: Optional[str] = None
    priority: str
    job_description: Optional[str] = None
    existing_cv_url: Optional[str] = None
    raw_data: CVDataSchema
    status: str
    assigned_to_id: Optional[str] = None
    access_token: str
    created_at: datetime
    updated_at: datetime
    activities: List[ActivityLogResponse] = []

    class Config:
        from_attributes = True


class SubmissionStatusUpdate(BaseModel):
    status: str


class SubmissionAssign(BaseModel):
    assigned_to_id: str
