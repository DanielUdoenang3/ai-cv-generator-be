from fastapi import APIRouter
from app.api.controller.admin.staff import (
    get_staff_list_controller,
    create_staff_member_controller,
    delete_staff_member_controller,
)

admin_staff_router = APIRouter(prefix="/staff", tags=["Admin Staff Management"])

admin_staff_router.add_api_route(
    "",
    endpoint=get_staff_list_controller,
    methods=["GET"],
    summary="List Staff Members",
    description="Fetch a list of staff members with stats (Total Staff, Active Members, Avg. Workload, individual workloads).",
)

admin_staff_router.add_api_route(
    "",
    endpoint=create_staff_member_controller,
    methods=["POST"],
    summary="Create Staff Member",
    description="Register a new admin/staff member. Restricted to Super Admin.",
)

admin_staff_router.add_api_route(
    "/{staff_id}",
    endpoint=delete_staff_member_controller,
    methods=["DELETE"],
    summary="Delete Staff Member",
    description="Delete a staff member. Tasks assigned to them are automatically unassigned and logged in history. Restricted to Super Admin.",
)
