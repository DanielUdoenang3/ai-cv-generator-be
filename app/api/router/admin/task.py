from fastapi import APIRouter
from app.api.controller.admin.task import (
    get_tasks_controller,
    create_task_controller,
    get_task_by_id_controller,
    update_task_controller,
    delete_task_controller,
)

admin_task_router = APIRouter(prefix="/tasks", tags=["Admin Task Management"])

admin_task_router.add_api_route(
    "",
    endpoint=get_tasks_controller,
    methods=["GET"],
    summary="Get Tasks & Metrics",
    description="Retrieve Kanban task cards and overview stat metrics.",
)

admin_task_router.add_api_route(
    "",
    endpoint=create_task_controller,
    methods=["POST"],
    summary="Create Task",
    description="Create a new task card.",
)

admin_task_router.add_api_route(
    "/{task_id}",
    endpoint=get_task_by_id_controller,
    methods=["GET"],
    summary="Get Task Details",
    description="Fetch single task card details.",
)

admin_task_router.add_api_route(
    "/{task_id}",
    endpoint=update_task_controller,
    methods=["PATCH"],
    summary="Update Task",
    description="Update task fields, assignee, priority, or status column.",
)

admin_task_router.add_api_route(
    "/{task_id}",
    endpoint=delete_task_controller,
    methods=["DELETE"],
    summary="Delete Task",
    description="Delete a task card.",
)
