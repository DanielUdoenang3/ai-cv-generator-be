from datetime import datetime, timezone

from fastapi import status
from sqlalchemy.orm import Session

from app.models.admins import Admin
from app.models.invitations import AdminInvitation
from app.models.enums import AdminRole
from app.schema.staff import InviteAdminRequest, AcceptInviteRequest, DeclineInviteRequest
from app.utils.custom_response import success_response, error_response
from app.utils.token import create_invite_token, decode_invite_token
from app.utils.pass_hash import hash_password
from app.utils.settings import settings
from app.services.email_services import send_admin_invite_email


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_valid_role(role: str) -> bool:
    return role in (AdminRole.SUPER_ADMIN.value, AdminRole.SUB_ADMIN.value)


def _serialise_invite(invite: AdminInvitation, invited_by: Admin | None = None) -> dict:
    return {
        "id": invite.id,
        "email": invite.email,
        "role": invite.role,
        "status": invite.status,
        "expires_at": invite.expires_at,
        "invited_by": (
            {
                "id": invited_by.id,
                "first_name": invited_by.first_name,
                "last_name": invited_by.last_name,
                "email": invited_by.email,
            }
            if invited_by
            else None
        ),
        "created_at": invite.created_at,
        "updated_at": invite.updated_at,
    }


def _mark_expired_invites(db: Session) -> None:
    """Flip pending invites whose expiry has passed to 'expired' in bulk."""
    now = datetime.now(timezone.utc)
    (
        db.query(AdminInvitation)
        .filter(
            AdminInvitation.status == "pending",
            AdminInvitation.expires_at < now,
        )
        .update({"status": "expired"}, synchronize_session=False)
    )
    db.commit()


# ---------------------------------------------------------------------------
# 1. Send an invitation
# ---------------------------------------------------------------------------

async def send_invitation(
    data: InviteAdminRequest,
    current_admin: Admin,
    db: Session,
):
    """
    Super admin sends an invitation to an email address with a specified role.

    Rules:
    - Target email must not already belong to an active admin.
    - A pending, non-expired invite for the same email is blocked (prevents spam).
    - A new JWT invite token is created (7-day expiry) and persisted.
    - An invitation email is dispatched via Resend.
    """
    if not _is_valid_role(data.role):
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=f"Invalid role '{data.role}'. Must be 'super_admin' or 'sub_admin'.",
        )

    email_lower = data.email.lower().strip()

    # Block if the email already belongs to an admin
    existing_admin = db.query(Admin).filter(Admin.email == email_lower).first()
    if existing_admin:
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="An admin with this email already exists.",
        )

    # Block if there is already a live pending invite for this email
    _mark_expired_invites(db)
    existing_invite = (
        db.query(AdminInvitation)
        .filter(
            AdminInvitation.email == email_lower,
            AdminInvitation.status == "pending",
        )
        .first()
    )
    if existing_invite:
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="A pending invitation has already been sent to this email. "
                    "Revoke it first before sending a new one.",
        )

    # Generate token
    token, expires_at = create_invite_token(email_lower, data.role)

    invite = AdminInvitation(
        email=email_lower,
        role=data.role,
        token=token,
        expires_at=expires_at,
        status="pending",
        invited_by_id=current_admin.id,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)

    # Build the invite link the frontend will handle
    invite_link = f"{settings.DASHBOARD}/accept-invite?token={token}"
    inviter_name = f"{current_admin.first_name} {current_admin.last_name}"

    await send_admin_invite_email(
        to_email=email_lower,
        inviter_name=inviter_name,
        role=data.role,
        invite_link=invite_link,
        expires_at=expires_at,
    )

    return success_response(
        status_code=status.HTTP_201_CREATED,
        message=f"Invitation sent to {email_lower}.",
        data=_serialise_invite(invite, current_admin),
    )


# ---------------------------------------------------------------------------
# 2. Verify an invitation token (public — no auth required)
# ---------------------------------------------------------------------------

async def verify_invitation(token: str, db: Session):
    """
    Called by the frontend before rendering the accept/decline page.
    Returns the invite details (email, role, inviter) so the UI can display them.
    """
    payload = decode_invite_token(token)
    if not payload:
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="This invitation link is invalid or has expired.",
        )

    invite = (
        db.query(AdminInvitation)
        .filter(AdminInvitation.token == token)
        .first()
    )

    if not invite:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Invitation not found.",
        )

    # Enforce DB-level expiry / status
    now = datetime.now(timezone.utc)
    stored_expiry = invite.expires_at
    if stored_expiry.tzinfo is None:
        stored_expiry = stored_expiry.replace(tzinfo=timezone.utc)

    if stored_expiry < now and invite.status == "pending":
        invite.status = "expired"
        db.commit()
        db.refresh(invite)

    if invite.status != "pending":
        status_messages = {
            "accepted": "This invitation has already been accepted.",
            "declined": "This invitation has already been declined.",
            "revoked":  "This invitation has been revoked by the admin.",
            "expired":  "This invitation has expired. Please ask for a new one.",
        }
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=status_messages.get(invite.status, "This invitation is no longer valid."),
        )

    inviter = db.query(Admin).filter(Admin.id == invite.invited_by_id).first()

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Invitation is valid.",
        data=_serialise_invite(invite, inviter),
    )


# ---------------------------------------------------------------------------
# 3. Accept an invitation (public — no auth required)
# ---------------------------------------------------------------------------

async def accept_invitation(data: AcceptInviteRequest, db: Session):
    """
    The invitee submits their details to complete registration.
    On success an access token is returned so the frontend can log them in.
    """
    from app.utils.token import create_access_token  # local import to avoid circular

    payload = decode_invite_token(data.token)
    if not payload:
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="This invitation link is invalid or has expired.",
        )

    invite = (
        db.query(AdminInvitation)
        .filter(AdminInvitation.token == data.token)
        .first()
    )
    if not invite:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Invitation not found.",
        )

    # Expiry / status check
    now = datetime.now(timezone.utc)
    stored_expiry = invite.expires_at
    if stored_expiry.tzinfo is None:
        stored_expiry = stored_expiry.replace(tzinfo=timezone.utc)

    if stored_expiry < now and invite.status == "pending":
        invite.status = "expired"
        db.commit()

    if invite.status != "pending":
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="This invitation is no longer valid.",
        )

    # Guard against the email being registered between invite creation and acceptance
    existing_admin = db.query(Admin).filter(Admin.email == invite.email).first()
    if existing_admin:
        invite.status = "accepted"
        db.commit()
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="An account with this email already exists.",
        )

    pass_hash = hash_password(data.password)
    if not pass_hash:
        return error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Password hashing failed.",
        )

    new_admin = Admin(
        first_name=data.first_name.strip(),
        last_name=data.last_name.strip(),
        email=invite.email,
        password=pass_hash,
        role=invite.role,
        phone=data.phone.strip() if data.phone else None,
        gender=data.gender,
        is_active=True,
        created_by=invite.invited_by_id,
    )
    db.add(new_admin)

    invite.status = "accepted"
    db.commit()
    db.refresh(new_admin)

    access_token = create_access_token(data={"email": new_admin.email})

    return success_response(
        status_code=status.HTTP_201_CREATED,
        message="Invitation accepted. Your account has been created.",
        data={
            "id": new_admin.id,
            "first_name": new_admin.first_name,
            "last_name": new_admin.last_name,
            "email": new_admin.email,
            "role": new_admin.role,
            "is_active": new_admin.is_active,
            "access_token": access_token,
        },
    )


# ---------------------------------------------------------------------------
# 4. Decline an invitation (public — no auth required)
# ---------------------------------------------------------------------------

async def decline_invitation(data: DeclineInviteRequest, db: Session):
    """The invitee explicitly declines — marks the invite as declined."""
    payload = decode_invite_token(data.token)
    if not payload:
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="This invitation link is invalid or has expired.",
        )

    invite = (
        db.query(AdminInvitation)
        .filter(AdminInvitation.token == data.token)
        .first()
    )
    if not invite:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Invitation not found.",
        )

    if invite.status != "pending":
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="This invitation is no longer active.",
        )

    invite.status = "declined"
    db.commit()

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Invitation declined.",
    )


# ---------------------------------------------------------------------------
# 5. List invitations (super admin only)
# ---------------------------------------------------------------------------

async def list_invitations(current_admin: Admin, db: Session):
    """
    Returns all invitations with their current status.
    Pending invites that have passed their expiry are auto-flipped to 'expired'.
    """
    _mark_expired_invites(db)

    invites = (
        db.query(AdminInvitation)
        .order_by(AdminInvitation.created_at.desc())
        .all()
    )

    # Bulk-fetch inviters to avoid N+1
    inviter_ids = list({inv.invited_by_id for inv in invites})
    inviters = (
        db.query(Admin).filter(Admin.id.in_(inviter_ids)).all()
        if inviter_ids
        else []
    )
    inviter_map = {a.id: a for a in inviters}

    data = [
        _serialise_invite(inv, inviter_map.get(inv.invited_by_id))
        for inv in invites
    ]

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Invitations fetched successfully.",
        data=data,
    )


# ---------------------------------------------------------------------------
# 6. Revoke an invitation (super admin only)
# ---------------------------------------------------------------------------

async def revoke_invitation(invitation_id: str, current_admin: Admin, db: Session):
    """Super admin cancels a pending invitation before it is acted on."""
    invite = (
        db.query(AdminInvitation)
        .filter(AdminInvitation.id == invitation_id)
        .first()
    )
    if not invite:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Invitation not found.",
        )

    if invite.status != "pending":
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=f"Cannot revoke an invitation that is already '{invite.status}'.",
        )

    invite.status = "revoked"
    db.commit()
    db.refresh(invite)

    inviter = db.query(Admin).filter(Admin.id == invite.invited_by_id).first()

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Invitation revoked successfully.",
        data=_serialise_invite(invite, inviter),
    )
