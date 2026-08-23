from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from app.models.enums import AdminRole

class StaffCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    role: str = Field(default=AdminRole.SUB_ADMIN.value)
    phone: Optional[str] = None
    gender: Optional[str] = None
