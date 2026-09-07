from fastapi import APIRouter
from app.api.controller.admin.auth import (
    create_admin_controller,
    login_admin_controller,
    get_admin_profile_controller,
    update_admin_profile_controller,
    forgot_password_controller,
    reset_password_controller,
)

admin_auth_router = APIRouter(prefix="/auth", tags=["Admin Authentication"])

admin_auth_router.add_api_route(
    "/create-admin",
    endpoint=create_admin_controller,
    methods=["POST"],
    summary="Create Admin",
    description="Create a new admin",
)

admin_auth_router.add_api_route(
    "/login",
    endpoint=login_admin_controller,
    methods=["POST"],
    summary="Admin Login",
    description="Login an admin",
)

admin_auth_router.add_api_route(
    "/profile",
    endpoint=get_admin_profile_controller,
    methods=["GET"],
    summary="Get Admin Profile",
    description="Get the profile of the authenticated admin",
)

admin_auth_router.add_api_route(
    "/profile",
    endpoint=update_admin_profile_controller,
    methods=["PUT"],
    summary="Update Admin Profile",
    description="Update the profile of the authenticated admin",
)

admin_auth_router.add_api_route(
    "/forgot-password",
    endpoint=forgot_password_controller,
    methods=["POST"],
    summary="Forgot Password",
    description="Request a magic-link password reset email. Available to super admins and sub admins only.",
)

admin_auth_router.add_api_route(
    "/reset-password",
    endpoint=reset_password_controller,
    methods=["POST"],
    summary="Reset Password",
    description="Verify the magic-link token and set a new password. Returns an access token on success.",
)

