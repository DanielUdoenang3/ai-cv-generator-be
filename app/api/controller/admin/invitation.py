from fastapi import Depends
from sqlalchemy.orm import Session

from app.utils.database import get_db
from app.models.admins import Admin
from app.schema.staff import InviteAdminRequest, AcceptInviteRequest, DeclineInviteRequest
from app.services import get_current_super_admin
from app.services.admin.invitation import (
    send_invitation,
    verify_invitation,
    accept_invitation,
    decline_invitation,
    list_invitations,
    revoke_invitation,
)


async def send_invitation_controller(
    data: InviteAdminRequest,
    current_admin: Admin = Depends(get_current_super_admin),
    db: Session = Depends(get_db),
):
    return await send_invitation(data=data, current_admin=current_admin, db=db)


async def verify_invitation_controller(
    token: str,
    db: Session = Depends(get_db),
):
    return await verify_invitation(token=token, db=db)


async def accept_invitation_controller(
    data: AcceptInviteRequest,
    db: Session = Depends(get_db),
):
    return await accept_invitation(data=data, db=db)


async def decline_invitation_controller(
    data: DeclineInviteRequest,
    db: Session = Depends(get_db),
):
    return await decline_invitation(data=data, db=db)


async def list_invitations_controller(
    current_admin: Admin = Depends(get_current_super_admin),
    db: Session = Depends(get_db),
):
    return await list_invitations(current_admin=current_admin, db=db)


async def revoke_invitation_controller(
    invitation_id: str,
    current_admin: Admin = Depends(get_current_super_admin),
    db: Session = Depends(get_db),
):
    return await revoke_invitation(
        invitation_id=invitation_id, current_admin=current_admin, db=db
    )
