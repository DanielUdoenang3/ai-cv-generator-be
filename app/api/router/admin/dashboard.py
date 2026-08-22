from fastapi import APIRouter
from app.api.controller.admin.dashboard import (
    get_dashboard_stats_controller,
    get_recent_submissions_controller,
)

admin_dashboard_router = APIRouter(prefix="/dashboard", tags=["Admin Dashboard"])

admin_dashboard_router.add_api_route(
    "/stats",
    endpoint=get_dashboard_stats_controller,
    methods=["GET"],
    summary="Get Dashboard Stats",
    description="Retrieve overview metrics for dashboard cards. Filtered by role permissions.",
)

admin_dashboard_router.add_api_route(
    "/recent-submissions",
    endpoint=get_recent_submissions_controller,
    methods=["GET"],
    summary="Get Recent Submissions",
    description="Query a paginated, sortable, and filterable list of recent submissions.",
)
