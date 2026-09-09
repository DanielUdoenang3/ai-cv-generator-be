from fastapi import APIRouter

from app.api.controller.admin.invitation import (
    send_invitation_controller,
    verify_invitation_controller,
    accept_invitation_controller,
    decline_invitation_controller,
    list_invitations_controller,
    revoke_invitation_controller,
)

admin_invitation_router = APIRouter(prefix="/invitations", tags=["Admin Invitations"])

# ── Super-admin protected ────────────────────────────────────────────────────

admin_invitation_router.add_api_route(
    "",
    endpoint=send_invitation_controller,
    methods=["POST"],
    summary="Send Admin Invitation",
    description=(
        "Send an invitation email to a new admin. "
        "A 7-day signed token is generated and emailed to the target address. "
        "Restricted to Super Admin."
    ),
)

admin_invitation_router.add_api_route(
    "",
    endpoint=list_invitations_controller,
    methods=["GET"],
    summary="List All Invitations",
    description=(
        "Fetch all admin invitations with their current status "
        "(pending / accepted / declined / revoked / expired). "
        "Restricted to Super Admin."
    ),
)

admin_invitation_router.add_api_route(
    "/{invitation_id}/revoke",
    endpoint=revoke_invitation_controller,
    methods=["PATCH"],
    summary="Revoke Invitation",
    description=(
        "Cancel a pending invitation before it is acted on. "
        "Restricted to Super Admin."
    ),
)

# ── Public (token is the proof of identity) ──────────────────────────────────

admin_invitation_router.add_api_route(
    "/verify",
    endpoint=verify_invitation_controller,
    methods=["GET"],
    summary="Verify Invitation Token",
    description=(
        "Verify an invitation token and return invite details (email, role, inviter). "
        "Called by the frontend before rendering the accept/decline page. "
        "No authentication required."
    ),
)

admin_invitation_router.add_api_route(
    "/accept",
    endpoint=accept_invitation_controller,
    methods=["POST"],
    summary="Accept Invitation",
    description=(
        "Complete registration by submitting personal details against a valid token. "
        "Returns an access token on success so the frontend can log the user in. "
        "No authentication required."
    ),
)

admin_invitation_router.add_api_route(
    "/decline",
    endpoint=decline_invitation_controller,
    methods=["POST"],
    summary="Decline Invitation",
    description=(
        "Decline an invitation. Marks the invite as declined so it cannot be reused. "
        "No authentication required."
    ),
)
