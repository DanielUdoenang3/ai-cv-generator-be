from sqlalchemy import Column, String, DateTime
from app.models.base_models import BaseModel


class AdminInvitation(BaseModel):
    """
    Tracks pending admin invitations.

    Lifecycle:
        pending  → accepted  (invitee completed registration)
        pending  → declined  (invitee explicitly declined)
        pending  → expired   (7-day window passed, enforced at query time)
        pending  → revoked   (super admin cancelled the invite before it was acted on)
    """

    __tablename__ = "admin_invitations"

    # Who is being invited
    email: str = Column(String, nullable=False, index=True)

    # "super_admin" | "sub_admin"
    role: str = Column(String, nullable=False)

    # Signed JWT (7-day expiry baked in)
    token: str = Column(String, unique=True, index=True, nullable=False)

    # UTC datetime at which the token expires
    expires_at: str = Column(DateTime(timezone=True), nullable=False)

    # pending | accepted | declined | revoked
    status: str = Column(String, nullable=False, default="pending")

    # FK to Admin.id — who sent the invite
    invited_by_id: str = Column(String, nullable=False)

    def __repr__(self):
        return (
            f"AdminInvitation(id={self.id}, email={self.email}, "
            f"role={self.role}, status={self.status})"
        )
