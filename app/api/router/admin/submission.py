from fastapi import APIRouter
from app.api.controller.admin.submission import (
    get_all_submissions_controller,
    get_single_submission_controller,
    assign_submission_controller,
    update_submission_status_controller,
    get_submission_messages_controller,
    send_admin_message_controller,
)

admin_submission_router = APIRouter(prefix="/submissions", tags=["Admin Submission Management"])

admin_submission_router.add_api_route(
    "",
    endpoint=get_all_submissions_controller,
    methods=["GET"],
    summary="List All Submissions",
    description=(
        "Super Admin/Admin: returns all submissions ordered by newest. "
        "Sub-Admin/Moderator: returns only submissions assigned to their account."
    ),
)

admin_submission_router.add_api_route(
    "/{submission_id}",
    endpoint=get_single_submission_controller,
    methods=["GET"],
    summary="Get Submission Details",
    description="Fetch full details of a single submission. Sub-Admins can only access their assigned submissions.",
)

admin_submission_router.add_api_route(
    "/{submission_id}/assign",
    endpoint=assign_submission_controller,
    methods=["PATCH"],
    summary="Assign Submission",
    description=(
        "Assign or reassign a submission to a specific staff member. "
        "Restricted to Super Admin and Admin roles only. "
        "Automatically escalates status from 'new' to 'in_progress' on first assignment."
    ),
)

admin_submission_router.add_api_route(
    "/{submission_id}/status",
    endpoint=update_submission_status_controller,
    methods=["PATCH"],
    summary="Update Submission Status",
    description="Update the status of a submission. Sub-Admins can only update their assigned submissions.",
)

admin_submission_router.add_api_route(
    "/{submission_id}/messages",
    endpoint=get_submission_messages_controller,
    methods=["GET"],
    summary="Get Conversation Messages",
    description="Fetch the full chat history for a submission including client and staff messages.",
)

admin_submission_router.add_api_route(
    "/{submission_id}/messages",
    endpoint=send_admin_message_controller,
    methods=["POST"],
    summary="Send Message to Client",
    description=(
        "Allows authenticated staff to reply in a client's chat. "
        "Message is permanently stamped with the sender's identity from their JWT session."
    ),
)
