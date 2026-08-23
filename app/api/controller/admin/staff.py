from fastapi import Depends
from sqlalchemy.orm import Session
from app.utils.database import get_db
from app.models.admins import Admin
from app.schema.staff import StaffCreate
from app.services import get_current_admin, get_current_super_admin
from app.services.admin.staff import get_staff_list, create_staff_member, delete_staff_member

async def get_staff_list_controller(
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return await get_staff_list(current_admin=current_admin, db=db)

async def create_staff_member_controller(
    data: StaffCreate,
    current_admin: Admin = Depends(get_current_super_admin),
    db: Session = Depends(get_db),
):
    return await create_staff_member(data=data, db=db)

async def delete_staff_member_controller(
    staff_id: str,
    current_admin: Admin = Depends(get_current_super_admin),
    db: Session = Depends(get_db),
):
    return await delete_staff_member(staff_id=staff_id, current_admin=current_admin, db=db)
