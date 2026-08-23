from fastapi import Depends
from sqlalchemy.orm import Session
from app.utils.database import get_db
from app.schema.auth import CreateAdmin, AdminLogin, AdminProfileUpdate
from app.services.admin.auth import create_admin, login_admin, get_admin_profile, update_admin_profile
from app.models.admins import Admin

from app.services import get_current_admin, get_current_super_admin, get_current_sub_admin

async def create_admin_controller(
    data: CreateAdmin,
    # current_admin: Admin = Depends(get_current_super_admin),
    db: Session = Depends(get_db),
):
    return await create_admin(data=data, db=db)

async def login_admin_controller(
    data: AdminLogin,
    db: Session = Depends(get_db),
):
    return await login_admin(data=data, db=db)

async def get_admin_profile_controller(
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return await get_admin_profile(current_admin=current_admin, db=db)

async def update_admin_profile_controller(
    data: AdminProfileUpdate,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return await update_admin_profile(current_admin=current_admin, data=data, db=db)