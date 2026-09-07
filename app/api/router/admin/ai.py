from fastapi import APIRouter
from app.api.controller.admin.ai import (
    generate_cv_controller,
    get_submission_generations_controller,
    get_ai_models_controller,
)

admin_ai_router = APIRouter(tags=["Admin AI Generation Engine"])

admin_ai_router.add_api_route(
    "/ai/models",
    get_ai_models_controller,
    methods=["GET"],
    summary="List available OpenAI chat models",
    description=(
        "Returns all chat-capable OpenAI models available for the Tailor Resume "
        "model-selection dropdown. Enriched with human-readable labels, tier badges, "
        "and cost notes. Falls back to a curated list if the API is unreachable."
    ),
)

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
