from fastapi import APIRouter
from app.api.controller.client.submission import (
    create_submission_controller,
    get_submission_status_controller,
)
from app.api.controller.client.chat import (
    get_messages_controller,
    send_message_controller,
)

client_router = APIRouter(prefix="/public", tags=["Public Client Submission & Chat"])

client_router.add_api_route(
    "/submissions",
    endpoint=create_submission_controller,
    methods=["POST"],
    summary="Create Client Submission",
    description="Submit raw resume data and target job details to start a CV generation flow.",
)

client_router.add_api_route(
    "/submissions/{submission_id}",
    endpoint=get_submission_status_controller,
    methods=["GET"],
    summary="Get Submission Status",
    description="Retrieve the current status of a CV request. Requires X-Client-Access-Token header.",
)

client_router.add_api_route(
    "/submissions/{submission_id}/messages",
    endpoint=get_messages_controller,
    methods=["GET"],
    summary="Get Conversation Messages",
    description="Fetch message history for a CV request. Requires X-Client-Access-Token header.",
)

client_router.add_api_route(
    "/submissions/{submission_id}/messages",
    endpoint=send_message_controller,
    methods=["POST"],
    summary="Send Message",
    description="Send a message to the support/assigned team. Requires X-Client-Access-Token header.",
)
