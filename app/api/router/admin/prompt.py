from fastapi import APIRouter
from app.api.controller.admin.prompt import (
    list_prompts_controller,
    create_prompt_controller,
    update_prompt_controller,
    activate_prompt_controller,
    deactivate_prompt_controller,
    duplicate_prompt_controller,
    delete_prompt_controller,
)

admin_prompt_router = APIRouter(tags=["Admin Master Prompts"])

admin_prompt_router.add_api_route(
    "/prompts",
    list_prompts_controller,
    methods=["GET"],
    summary="List all master system prompt templates and summary stats (Super Admin only)",
)

admin_prompt_router.add_api_route(
    "/prompts",
    create_prompt_controller,
    methods=["POST"],
    summary="Create a new master system prompt template or version (Super Admin only)",
)

admin_prompt_router.add_api_route(
    "/prompts/{prompt_id}",
    update_prompt_controller,
    methods=["PATCH"],
    summary="Edit an existing master system prompt template (Super Admin only)",
)

admin_prompt_router.add_api_route(
    "/prompts/{prompt_id}/activate",
    activate_prompt_controller,
    methods=["PATCH"],
    summary="Activate a master system prompt template (Super Admin only)",
)

admin_prompt_router.add_api_route(
    "/prompts/{prompt_id}/deactivate",
    deactivate_prompt_controller,
    methods=["PATCH"],
    summary="Deactivate a master system prompt template (Super Admin only)",
)

admin_prompt_router.add_api_route(
    "/prompts/{prompt_id}/duplicate",
    duplicate_prompt_controller,
    methods=["POST"],
    summary="Duplicate a master system prompt template (Super Admin only)",
)

admin_prompt_router.add_api_route(
    "/prompts/{prompt_id}",
    delete_prompt_controller,
    methods=["DELETE"],
    summary="Delete a master system prompt template (Super Admin only)",
)

