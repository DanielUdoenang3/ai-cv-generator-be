from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from app.models.admins import AdminRole

class AdminLogin(BaseModel):
    email: EmailStr
    password: str

class CreateAdmin(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    role: str = Field(default=AdminRole.SUB_ADMIN.value)
    phone: Optional[str] = None
    gender: Optional[str] = None

class AdminProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    gender: Optional[str] = None