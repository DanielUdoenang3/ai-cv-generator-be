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

# ---------------------------------------------------------------------------
# Invitation schemas
# ---------------------------------------------------------------------------

class InviteAdminRequest(BaseModel):
    """Sent by a super admin to create an invitation."""
    email: EmailStr
    role: str = Field(default=AdminRole.SUB_ADMIN.value)


class AcceptInviteRequest(BaseModel):
    """Sent by the invitee to complete registration."""
    token: str
    first_name: str
    last_name: str
    password: str
    phone: Optional[str] = None
    gender: Optional[str] = None

    from pydantic import field_validator

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v


class DeclineInviteRequest(BaseModel):
    """Sent by the invitee to decline the invitation."""
    token: str


class RevokeInviteRequest(BaseModel):
    """Sent by a super admin to cancel a pending invitation."""
    invitation_id: str
