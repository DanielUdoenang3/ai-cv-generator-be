from fastapi import status
from app.models.admins import Admin
from app.utils.custom_response import success_response, error_response
from sqlalchemy.orm import Session
from app.schema.auth import AdminLogin, CreateAdmin, AdminProfileUpdate, ForgotPasswordRequest, ResetPasswordRequest
from app.utils.token import decode_access_token, create_access_token, create_refresh_token, create_reset_token, decode_reset_token
from app.utils.settings import settings
from app.utils.pass_hash import verify_password, hash_password
from app.models.enums import AdminRole
from app.services.email_services import send_reset_password_email
from datetime import datetime, timezone


async def create_admin(data: CreateAdmin, db: Session):
    if not data:
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="All fields are required",
        )

    email_lower = data.email.lower().strip()

    existing_admin = db.query(Admin).filter(
        Admin.email == email_lower
    ).first()
    
    if existing_admin:
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Admin with this email already exists",
        )
    
    pass_hash = hash_password(data.password)

    if not pass_hash:
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Password hashing failed",
        )

    new_admin = Admin(
        first_name=data.first_name,
        last_name=data.last_name,
        email=email_lower,
        password=pass_hash,
        role=data.role,
        phone=data.phone,
        gender=data.gender,
        is_active=True,
    )

    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)

    return success_response(
        status_code=status.HTTP_201_CREATED,
        message="Admin created successfully",
        data={
            "id": new_admin.id,
            "first_name": new_admin.first_name,
            "last_name": new_admin.last_name,
            "email": new_admin.email,
            "role": new_admin.role,
            "gender": new_admin.gender,
            "phone": new_admin.phone,
            "is_active": new_admin.is_active,
        }
    )

async def login_admin(data: AdminLogin, db: Session):
    if not data:
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="All fields are required",
        )

    email_lower = data.email.lower().strip()

    existing_admin = db.query(Admin).filter(
        Admin.email == email_lower
    ).first()
    
    if not existing_admin:
        return error_response(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message="User not found",
        )

    if not verify_password(data.password, existing_admin.password):
        return error_response(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message="Invalid credentials",
        )

    if not existing_admin.is_active:
        return error_response(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Admin is not active",
        )

    access_token = create_access_token(data={"email":existing_admin.email})
    # refresh_token = create_refresh_token(data={"email":existing_admin.email})

    existing_admin.last_login = datetime.now(timezone.utc)
    db.commit()
    db.refresh(existing_admin)

    response_data = {
        "id": existing_admin.id,
        "first_name": existing_admin.first_name,
        "last_name": existing_admin.last_name,
        "email": existing_admin.email,
        "role": existing_admin.role,
        "gender": existing_admin.gender,
        "phone": existing_admin.phone,
        "is_active": existing_admin.is_active,
        "access_token": access_token,
    }

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Admin logged in successfully",
        data=response_data
    )

async def get_admin_profile(db: Session, current_admin: Admin):
    return success_response(
        status_code=status.HTTP_200_OK,
        message="Admin profile fetched successfully",
        data={
            "id": current_admin.id,
            "first_name": current_admin.first_name,
            "last_name": current_admin.last_name,
            "email": current_admin.email,
            "role": current_admin.role,
            "gender": current_admin.gender,
            "phone": current_admin.phone,
            "is_active": current_admin.is_active,
            "last_login": current_admin.last_login,
            "created_at": current_admin.created_at,
            "updated_at": current_admin.updated_at,
        }
    )


async def update_admin_profile(current_admin: Admin, data: AdminProfileUpdate, db: Session):
    if not data:
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="No update data provided",
        )

    email_changed = False
    if data.email is not None:
        email_lower = data.email.lower().strip()
        if email_lower != current_admin.email:
            existing_email = db.query(Admin).filter(Admin.email == email_lower).first()
            if existing_email:
                return error_response(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="Email is already taken by another admin",
                )
            current_admin.email = email_lower
            email_changed = True

    if data.first_name is not None:
        current_admin.first_name = data.first_name.strip()
    if data.last_name is not None:
        current_admin.last_name = data.last_name.strip()
    if data.phone is not None:
        current_admin.phone = data.phone.strip()
    if data.gender is not None:
        current_admin.gender = data.gender

    db.commit()
    db.refresh(current_admin)

    access_token = None
    if email_changed:
        access_token = create_access_token(data={"email": current_admin.email})

    res_data = {
        "id": current_admin.id,
        "first_name": current_admin.first_name,
        "last_name": current_admin.last_name,
        "email": current_admin.email,
        "role": current_admin.role,
        "gender": current_admin.gender,
        "phone": current_admin.phone,
        "is_active": current_admin.is_active,
        "created_at": current_admin.created_at,
        "updated_at": current_admin.updated_at,
    }
    if access_token:
        res_data["access_token"] = access_token

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Profile updated successfully",
        data=res_data
    )


async def forgot_password(data: ForgotPasswordRequest, db: Session):
    """
    Step 1 of magic-link flow.
    Looks up the email, confirms it belongs to a super_admin or sub_admin,
    generates a short-lived reset token, persists it, and dispatches the email.

    We always return a generic 200 so we don't leak whether the email exists.
    """
    email_lower = data.email.lower().strip()

    admin = db.query(Admin).filter(
        Admin.email == email_lower,
        Admin.is_active == True,
        Admin.role.in_([AdminRole.SUPER_ADMIN.value, AdminRole.SUB_ADMIN.value]),
    ).first()

    # Generic response regardless of outcome — prevents email enumeration
    generic_message = "If that email is registered, a reset link has been sent."

    if not admin:
        return success_response(
            status_code=status.HTTP_200_OK,
            message=generic_message,
        )

    # Generate token and persist it
    token, expires_at = create_reset_token(email_lower)
    admin.reset_token = token
    admin.reset_token_expires_at = expires_at
    db.commit()
    db.refresh(admin)

    # Build the magic link pointing at the frontend reset page
    reset_link = f"{settings.DASHBOARD}/reset-password?token={token}"

    # Fire the email (non-blocking failure — we still return 200)
    await send_reset_password_email(
        to_email=admin.email,
        first_name=admin.first_name,
        role=admin.role,
        reset_link=reset_link,
        expires_at=expires_at,
    )

    return success_response(
        status_code=status.HTTP_200_OK,
        message=generic_message,
    )


async def reset_password(data: ResetPasswordRequest, db: Session):
    """
    Step 2 of magic-link flow.
    Validates the token, enforces expiry, updates the password,
    clears the token, and issues a fresh access token so the frontend
    can log the user straight into their dashboard.
    """
    email = decode_reset_token(data.token)

    if not email:
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="This reset link is invalid or has expired. Please request a new one.",
        )

    admin = db.query(Admin).filter(
        Admin.email == email,
        Admin.is_active == True,
        Admin.role.in_([AdminRole.SUPER_ADMIN.value, AdminRole.SUB_ADMIN.value]),
    ).first()

    if not admin:
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="This reset link is invalid or has expired. Please request a new one.",
        )

    # Double-check token matches what is stored (guards against token reuse after invalidation)
    if admin.reset_token != data.token:
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="This reset link has already been used. Please request a new one.",
        )

    # Double-check expiry at the DB level (belt-and-suspenders over JWT exp).
    # Postgres may return a naive datetime; normalise both sides to UTC before comparing.
    if admin.reset_token_expires_at is None:
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="This reset link has expired. Please request a new one.",
        )

    stored_expiry = admin.reset_token_expires_at
    if stored_expiry.tzinfo is None:
        # Treat naive datetime from DB as UTC
        stored_expiry = stored_expiry.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) > stored_expiry:
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="This reset link has expired. Please request a new one.",
        )

    # Hash and save the new password, then invalidate the token immediately
    admin.password = hash_password(data.new_password)
    admin.reset_token = None
    admin.reset_token_expires_at = None
    admin.last_login = datetime.now(timezone.utc)
    db.commit()
    db.refresh(admin)

    # Issue a fresh access token so the frontend can redirect straight to the dashboard
    access_token = create_access_token(data={"email": admin.email})

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Password reset successfully. Welcome back!",
        data={
            "id": admin.id,
            "first_name": admin.first_name,
            "last_name": admin.last_name,
            "email": admin.email,
            "role": admin.role,
            "is_active": admin.is_active,
            "access_token": access_token,
        },
    )
