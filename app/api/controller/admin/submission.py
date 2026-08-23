from typing import Optional, List
from fastapi import Depends, Request, Form, File, UploadFile, Query
from sqlalchemy.orm import Session

from app.utils.database import get_db
from app.models.admins import Admin
from app.schema.submission import SubmissionStatusUpdate, SubmissionAssign
from app.schema.chat import MessageCreate, MessageEdit
from app.services import get_current_admin, get_current_super_admin
from app.services.admin.submission import (
    get_all_submissions,
    get_single_submission,
    assign_submission,
    unassign_submission,
    update_submission_status,
    get_submission_messages,
    send_admin_message,
    edit_admin_message,
    delete_admin_message,
    mark_admin_messages_read,
)


async def get_all_submissions_controller(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search term for client details or target role/ID"),
    status: Optional[str] = Query(None, description="Filter submissions by status"),
    assigned_to_id: Optional[str] = Query(None, description="Filter submissions by assigned staff ID"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort direction (asc, desc)"),
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return await get_all_submissions(
        current_admin=current_admin,
        db=db,
        page=page,
        limit=limit,
        search=search,
        status_filter=status,
        assigned_to_id=assigned_to_id,
        sort_by=sort_by,
        sort_order=sort_order,
    )


async def get_single_submission_controller(
    submission_id: str,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return await get_single_submission(
        submission_id=submission_id,
        current_admin=current_admin,
        db=db,
    )


async def assign_submission_controller(
    submission_id: str,
    data: SubmissionAssign,
    current_admin: Admin = Depends(get_current_super_admin),
    db: Session = Depends(get_db),
):
    return await assign_submission(
        submission_id=submission_id,
        data=data,
        current_admin=current_admin,
        db=db,
    )


async def update_submission_status_controller(
    submission_id: str,
    data: SubmissionStatusUpdate,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return await update_submission_status(
        submission_id=submission_id,
        data=data,
        current_admin=current_admin,
        db=db,
    )


async def get_submission_messages_controller(
    submission_id: str,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return await get_submission_messages(
        submission_id=submission_id,
        current_admin=current_admin,
        db=db,
    )


async def send_admin_message_controller(
    submission_id: str,
    message: Optional[str] = Form(None),
    files: Optional[List[UploadFile]] = File(None),
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Clean admin chat message endpoint.
    Accepts text message and/or direct file attachments (uploaded automatically to Cloudinary).
    """
    return await send_admin_message(
        submission_id=submission_id,
        current_admin=current_admin,
        db=db,
        message_text=message,
        raw_files=files,
     )


async def unassign_submission_controller(
    submission_id: str,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return await unassign_submission(
        submission_id=submission_id,
        current_admin=current_admin,
        db=db,
    )


async def edit_admin_message_controller(
    submission_id: str,
    message_id: str,
    data: MessageEdit,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Edit a staff message. Sub-admins can only edit their own messages."""
    return await edit_admin_message(
        submission_id=submission_id,
        message_id=message_id,
        data=data,
        current_admin=current_admin,
        db=db,
    )


async def delete_admin_message_controller(
    submission_id: str,
    message_id: str,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Delete any message in the conversation. Sub-admins restricted to assigned submissions."""
    return await delete_admin_message(
        submission_id=submission_id,
        message_id=message_id,
        current_admin=current_admin,
        db=db,
    )


async def mark_admin_read_controller(
    submission_id: str,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Mark all unread client messages as read."""
    return await mark_admin_messages_read(
        submission_id=submission_id,
        current_admin=current_admin,
        db=db,
    )
