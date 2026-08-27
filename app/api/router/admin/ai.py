from fastapi import APIRouter
from app.api.controller.admin.ai import (
    generate_cv_controller,
    get_submission_generations_controller,
)

admin_ai_router = APIRouter(tags=["Admin AI Generation Engine"])

admin_ai_router.add_api_route(
    "/submissions/{submission_id}/generate",
    generate_cv_controller,
    methods=["POST"],
    summary="Trigger AI CV generation for a client submission (OpenAI / Gemini)",
)

admin_ai_router.add_api_route(
    "/submissions/{submission_id}/generations",
    get_submission_generations_controller,
    methods=["GET"],
    summary="Fetch AI generation token logs and cost history for a submission",
)
