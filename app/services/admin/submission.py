from fastapi import status
from sqlalchemy.orm import Session

from app.models.admins import Admin
from app.models.submissions import Submission
from app.models.chats import Conversation, Message
from app.models.enums import SubmissionStatus, AdminRole, MessageSenderType
from app.schema.submission import SubmissionStatusUpdate, SubmissionAssign
from app.schema.chat import MessageCreate
from app.utils.custom_response import success_response, error_response


def _serialize_submission(submission: Submission) -> dict:
    """Internal helper — serializes a Submission ORM object to a clean dict."""
    client = submission.client
    assigned_to = submission.assigned_to

    return {
        "id": submission.id,
        "status": submission.status,
        "target_position": submission.target_position,
        "job_description": submission.job_description,
        "existing_cv_url": submission.existing_cv_url,
        "raw_data": submission.raw_data,
        "created_at": str(submission.created_at),
        "updated_at": str(submission.updated_at),
        "client": {
            "id": client.id,
            "first_name": client.first_name,
            "last_name": client.last_name,
            "email": client.email,
            "phone": client.phone,
        } if client else None,
        "assigned_to": {
            "id": assigned_to.id,
            "first_name": assigned_to.first_name,
            "last_name": assigned_to.last_name,
            "role": assigned_to.role,
        } if assigned_to else None,
    }


async def get_all_submissions(current_admin: Admin, db: Session):
    """
    Super Admin / Admin: returns ALL submissions ordered by newest first.
    Sub-Admin / Moderator: returns ONLY submissions assigned to their account.
    """

    if current_admin.role in [AdminRole.SUPER_ADMIN.value]:
        submissions = (
            db.query(Submission)
            .order_by(Submission.created_at.desc())
            .all()
        )
    else:
        submissions = (
            db.query(Submission)
            .filter(Submission.assigned_to_id == current_admin.id)
            .order_by(Submission.created_at.desc())
            .all()
        )

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Submissions fetched successfully",
        data={
            "total": len(submissions),
            "submissions": [_serialize_submission(s) for s in submissions],
        },
    )


async def get_single_submission(
    submission_id: str,
    current_admin: Admin,
    db: Session,
):
    """
    Retrieves a single submission by ID.
    Sub-Admins can only view submissions assigned to them.
    """

    submission = db.query(Submission).filter(
        Submission.id == submission_id
    ).first()

    if not submission:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Submission not found",
        )

    # Enforce access control for sub-admins and moderators
    is_restricted = current_admin.role in [
        AdminRole.SUB_ADMIN.value,
    ]
    if is_restricted and submission.assigned_to_id != current_admin.id:
        return error_response(
            status_code=status.HTTP_403_FORBIDDEN,
            message="You do not have permission to view this submission",
        )

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Submission fetched successfully",
        data=_serialize_submission(submission),
    )


async def assign_submission(
    submission_id: str,
    data: SubmissionAssign,
    current_admin: Admin,
    db: Session,
):
    """
    Assigns or reassigns a submission to a specific admin account.
    Restricted to Super Admin and Admin roles only.
    """

    submission = db.query(Submission).filter(
        Submission.id == submission_id
    ).first()

    if not submission:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Submission not found",
        )

    # Confirm the target admin account exists and is active
    target_admin = db.query(Admin).filter(
        Admin.id == data.assigned_to_id,
        Admin.is_active == True,
    ).first()

    if not target_admin:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Target admin not found or is inactive",
        )

    submission.assigned_to_id = data.assigned_to_id

    # Auto-escalate status from NEW to IN_PROGRESS on first assignment
    if submission.status == SubmissionStatus.NEW.value:
        submission.status = SubmissionStatus.IN_PROGRESS.value

    db.commit()
    db.refresh(submission)

    return success_response(
        status_code=status.HTTP_200_OK,
        message=f"Submission successfully assigned to {target_admin.first_name} {target_admin.last_name}",
        data=_serialize_submission(submission),
    )


async def update_submission_status(
    submission_id: str,
    data: SubmissionStatusUpdate,
    current_admin: Admin,
    db: Session,
):
    """
    Updates the status of a submission.
    All staff roles can update status on their assigned submissions.
    """

    submission = db.query(Submission).filter(
        Submission.id == submission_id
    ).first()

    if not submission:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Submission not found",
        )

    # Enforce access control for sub-admins and moderators
    is_restricted = current_admin.role in [
        AdminRole.SUB_ADMIN.value,
    ]
    if is_restricted and submission.assigned_to_id != current_admin.id:
        return error_response(
            status_code=status.HTTP_403_FORBIDDEN,
            message="You do not have permission to update this submission",
        )

    # Validate status value against enum
    valid_statuses = [s.value for s in SubmissionStatus]
    if data.status not in valid_statuses:
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
        )

    submission.status = data.status
    db.commit()
    db.refresh(submission)

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Submission status updated successfully",
        data=_serialize_submission(submission),
    )


async def get_submission_messages(
    submission_id: str,
    current_admin: Admin,
    db: Session,
):
    """
    Returns the full conversation history for a submission.
    Sub-admins can only read messages in submissions assigned to them.
    """

    submission = db.query(Submission).filter(
        Submission.id == submission_id
    ).first()

    if not submission:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Submission not found",
        )

    is_restricted = current_admin.role in [
        AdminRole.SUB_ADMIN.value,
        AdminRole.MODERATOR.value,
    ]
    if is_restricted and submission.assigned_to_id != current_admin.id:
        return error_response(
            status_code=status.HTTP_403_FORBIDDEN,
            message="You do not have permission to view messages for this submission",
        )

    conversation = db.query(Conversation).filter(
        Conversation.submission_id == submission_id
    ).first()

    if not conversation:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="No conversation found for this submission",
        )

    messages = conversation.messages

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Messages fetched successfully",
        data={
            "conversation_id": conversation.id,
            "submission_id": submission_id,
            "submission_status": submission.status,
            "messages": [
                {
                    "id": msg.id,
                    "sender_type": msg.sender_type,
                    "sender_name": (
                        f"{msg.sender.first_name} {msg.sender.last_name}"
                        if msg.sender_type == MessageSenderType.STAFF.value and msg.sender
                        else submission.client.first_name
                    ),
                    "message": msg.message,
                    "attachments": msg.attachments,
                    "is_read": msg.is_read,
                    "created_at": str(msg.created_at),
                }
                for msg in messages
            ],
        },
    )


from typing import Optional, List, Any
from fastapi import UploadFile

from app.utils.cloudinary import upload_multiple_files_to_cloudinary


async def send_admin_message(
    submission_id: str,
    current_admin: Admin,
    db: Session,
    message_text: Optional[str] = None,
    attachments: Optional[List[Any]] = None,
    raw_files: Optional[List[UploadFile]] = None,
    data: Optional[MessageCreate] = None,
):
    """
    Allows any authenticated staff member to send a message in a submission's conversation.
    Supports JSON pre-uploaded attachment links AND direct raw file uploads to Cloudinary.
    """

    submission = db.query(Submission).filter(
        Submission.id == submission_id
    ).first()

    if not submission:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Submission not found",
        )

    is_restricted = current_admin.role in [
        AdminRole.SUB_ADMIN.value,
    ]
    if is_restricted and submission.assigned_to_id != current_admin.id:
        return error_response(
            status_code=status.HTTP_403_FORBIDDEN,
            message="You do not have permission to message in this submission",
        )

    conversation = db.query(Conversation).filter(
        Conversation.submission_id == submission_id
    ).first()

    if not conversation:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="No conversation found for this submission",
        )

    final_message = ""
    if data and data.message:
        final_message = data.message.strip()
    elif message_text:
        final_message = message_text.strip()

    final_attachments = []
    if data and data.attachments:
        final_attachments.extend(data.attachments)
    elif attachments:
        final_attachments.extend(attachments)

    if raw_files:
        uploaded_results = await upload_multiple_files_to_cloudinary(
            files=raw_files,
            folder="ai_cv_generator/chat_attachments",
        )
        final_attachments.extend(uploaded_results)

    if not final_message and not final_attachments:
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Message content or file attachments are required.",
        )

    message = Message(
        conversation_id=conversation.id,
        sender_type=MessageSenderType.STAFF.value,
        sender_id=current_admin.id,  # Links to exact staff member via JWT
        message=final_message,
        attachments=final_attachments if final_attachments else None,
        is_read=False,
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    return success_response(
        status_code=status.HTTP_201_CREATED,
        message="Message sent successfully",
        data={
            "id": message.id,
            "sender_type": message.sender_type,
            "sender_name": f"{current_admin.first_name} {current_admin.last_name}",
            "message": message.message,
            "attachments": message.attachments,
            "is_read": message.is_read,
            "created_at": str(message.created_at),
        },
    )
