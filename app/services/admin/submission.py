from datetime import datetime, timezone
from typing import Optional, List, Any

from fastapi import status, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.clients import Client
from app.models.admins import Admin
from app.models.submissions import Submission
from app.models.chats import Conversation, Message
from app.models.activities import SubmissionActivity
from app.models.enums import SubmissionStatus, AdminRole, MessageSenderType
from app.schema.submission import SubmissionStatusUpdate, SubmissionAssign
from app.schema.chat import MessageCreate, MessageEdit
from app.utils.cloudinary import upload_multiple_files_to_cloudinary
from app.utils.custom_response import success_response, error_response
from app.utils.websocket_manager import manager


def _serialize_submission(submission: Submission) -> dict:
    """Internal helper — serializes a Submission ORM object to a clean dict."""
    client = submission.client
    assigned_to = submission.assigned_to

    # Sort activities by id descending (newest first, UUID7 is chronologically sortable)
    activities = sorted(submission.activities, key=lambda a: a.id, reverse=True) if submission.activities else []
    serialized_activities = [
        {
            "id": act.id,
            "activity_type": act.activity_type,
            "title": act.title,
            "description": act.description,
            "actor_id": act.actor_id,
            "actor_name": act.actor.first_name + " " + act.actor.last_name if act.actor else None,
            "created_at": act.created_at,
        }
        for act in activities
    ]

    return {
        "id": submission.id,
        "reference_id": submission.reference_id,
        "status": submission.status,
        "target_position": submission.target_position,
        "target_company": submission.target_company,
        "priority": submission.priority,
        "job_description": submission.job_description,
        "existing_cv_url": submission.existing_cv_url,
        "raw_data": submission.raw_data,
        "created_at": submission.created_at,
        "updated_at": submission.updated_at,
        "activities": serialized_activities,
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


async def get_all_submissions(
    current_admin: Admin,
    db: Session,
    page: int = 1,
    limit: int = 10,
    search: Optional[str] = None,
    status_filter: Optional[str] = None,
    assigned_to_id: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
):
    """
    Returns a paginated, filterable, and sortable list of submissions.
    Super Admins/Admins can see all and filter by staff.
    Sub-Admins/Moderators can only see submissions assigned to them.
    """
    is_super = current_admin.role in [AdminRole.SUPER_ADMIN.value]

    # Base query joining Client to enable searching on client details
    query = db.query(Submission).outerjoin(Client, Submission.client_id == Client.id)

    # Enforce RBAC
    if not is_super:
        query = query.filter(Submission.assigned_to_id == current_admin.id)
    else:
        # Super admin filters by assigned staff member if provided
        if assigned_to_id:
            if assigned_to_id.lower() == "unassigned":
                query = query.filter(Submission.assigned_to_id.is_(None))
            else:
                query = query.filter(Submission.assigned_to_id == assigned_to_id)

    # Filter: search term (matches client details, target position, target company, or reference ID)
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Client.first_name.ilike(search_pattern),
                Client.last_name.ilike(search_pattern),
                Client.email.ilike(search_pattern),
                Submission.target_position.ilike(search_pattern),
                Submission.target_company.ilike(search_pattern),
                Submission.reference_id.ilike(search_pattern),
            )
        )

    # Filter: status
    if status_filter:
        query = query.filter(Submission.status == status_filter)

    # Sort
    valid_sort_fields = {
        "created_at": Submission.created_at,
        "updated_at": Submission.updated_at,
        "status": Submission.status,
        "target_position": Submission.target_position,
        "reference_id": Submission.reference_id,
        "priority": Submission.priority,
    }
    sort_column = valid_sort_fields.get(sort_by, Submission.created_at)

    if sort_order.lower() == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    # Pagination calculations
    total = query.count()
    pages = (total + limit - 1) // limit if total > 0 else 0
    offset = (page - 1) * limit

    submissions = query.offset(offset).limit(limit).all()

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Submissions fetched successfully",
        data={
            "total": total,
            "page": page,
            "limit": limit,
            "pages": pages,
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
    status_escalated = False
    if submission.status == SubmissionStatus.NEW.value:
        submission.status = SubmissionStatus.IN_PROGRESS.value
        status_escalated = True

    # Log assignment activity
    assign_activity = SubmissionActivity(
        submission_id=submission.id,
        activity_type="assigned",
        title=f"Assigned to {target_admin.first_name} {target_admin.last_name}",
        description="Submission assigned for review and processing",
        actor_id=current_admin.id,
    )
    db.add(assign_activity)

    if status_escalated:
        status_activity = SubmissionActivity(
            submission_id=submission.id,
            activity_type="status_changed",
            title="Status Changed to In Progress",
            description="Work started on CV generation and optimization",
            actor_id=current_admin.id,
        )
        db.add(status_activity)

    db.commit()
    db.refresh(submission)

    # Broadcast assignment event
    await manager.broadcast_to_submission(submission_id, {
        "event": "submission_assigned",
        "data": {
            "submission_id": submission_id,
            "assigned_to": {
                "id": target_admin.id,
                "name": f"{target_admin.first_name} {target_admin.last_name}",
                "role": target_admin.role,
            },
            "status_escalated": status_escalated,
        },
    })

    return success_response(
        status_code=status.HTTP_200_OK,
        message=f"Submission successfully assigned to {target_admin.first_name} {target_admin.last_name}",
        data=_serialize_submission(submission),
    )


async def unassign_submission(
    submission_id: str,
    current_admin: Admin,
    db: Session,
):
    """
    Clears the assignment of a submission (sets assigned_to_id to None).
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

    old_admin_id = submission.assigned_to_id
    if old_admin_id is None:
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Submission is already unassigned",
            data=_serialize_submission(submission),
        )

    # Fetch old admin info for the audit description
    old_admin = db.query(Admin).filter(Admin.id == old_admin_id).first()
    old_admin_name = f"{old_admin.first_name} {old_admin.last_name}" if old_admin else "Unknown Admin"

    submission.assigned_to_id = None

    # Log unassignment activity
    unassign_activity = SubmissionActivity(
        submission_id=submission.id,
        activity_type="assigned",
        title="Submission Unassigned",
        description=f"Staff member {old_admin_name} was unassigned from this submission by {current_admin.first_name} {current_admin.last_name}",
        actor_id=current_admin.id,
    )
    db.add(unassign_activity)
    db.commit()
    db.refresh(submission)

    # Broadcast unassignment event
    await manager.broadcast_to_submission(submission_id, {
        "event": "submission_assigned",
        "data": {
            "submission_id": submission_id,
            "assigned_to": None,
        },
    })

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Submission successfully unassigned",
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

    # Log status change activity
    status_titles = {
        "new": "New",
        "in_progress": "In Progress",
        "pending_client_input": "Pending Client Input",
        "ai_generated": "AI Generated",
        "review": "Review",
        "completed": "Completed",
        "rejected": "Rejected",
    }
    status_name = status_titles.get(data.status, data.status.replace("_", " ").title())

    status_descriptions = {
        "new": "Submission reverted to new status",
        "in_progress": "Work started on CV generation and optimization",
        "review": "Submission moved to review stage",
        "completed": "CV generation completed and finalized",
        "rejected": "Submission has been rejected",
    }
    description = status_descriptions.get(data.status, f"Submission status updated to {status_name}")

    status_activity = SubmissionActivity(
        submission_id=submission.id,
        activity_type="status_changed",
        title=f"Status Changed to {status_name}",
        description=description,
        actor_id=current_admin.id,
    )
    db.add(status_activity)

    old_status = submission.status
    submission.status = data.status
    db.commit()
    db.refresh(submission)

    # Broadcast status change event
    await manager.broadcast_to_submission(submission_id, {
        "event": "submission_status_changed",
        "data": {
            "submission_id": submission_id,
            "old_status": old_status,
            "new_status": submission.status,
            "changed_by": f"{current_admin.first_name} {current_admin.last_name}",
        },
    })

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

    payload = {
        "event": "new_message",
        "data": {
            "id": message.id,
            "sender_type": message.sender_type,
            "sender_name": f"{current_admin.first_name} {current_admin.last_name}",
            "message": message.message,
            "attachments": message.attachments,
            "is_read": message.is_read,
            "created_at": str(message.created_at),
            "updated_at": str(message.updated_at),
        },
    }
    await manager.broadcast_to_submission(submission_id, payload)

    return success_response(
        status_code=status.HTTP_201_CREATED,
        message="Message sent successfully",
        data=payload["data"],
    )


# ---------------------------------------------------------------------------
# EDIT ADMIN MESSAGE
# ---------------------------------------------------------------------------

async def edit_admin_message(
    submission_id: str,
    message_id: str,
    data: MessageEdit,
    current_admin: Admin,
    db: Session,
):
    """
    Allows staff to edit a message they personally sent.
    Super admins can edit any staff message.
    Broadcasts 'message_updated' WebSocket event.
    """
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        return error_response(status_code=status.HTTP_404_NOT_FOUND, message="Submission not found")

    is_restricted = current_admin.role in [AdminRole.SUB_ADMIN.value]
    if is_restricted and submission.assigned_to_id != current_admin.id:
        return error_response(
            status_code=status.HTTP_403_FORBIDDEN,
            message="You do not have permission to edit messages in this submission",
        )

    conversation = db.query(Conversation).filter(
        Conversation.submission_id == submission_id
    ).first()
    if not conversation:
        return error_response(status_code=status.HTTP_404_NOT_FOUND, message="No conversation found")

    # Staff can only edit their own messages; super_admin can edit any staff message
    filter_query = db.query(Message).filter(
        Message.id == message_id,
        Message.conversation_id == conversation.id,
        Message.sender_type == MessageSenderType.STAFF.value,
    )
    if is_restricted:
        filter_query = filter_query.filter(Message.sender_id == current_admin.id)

    message = filter_query.first()
    if not message:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Message not found or you do not have permission to edit it",
        )

    new_text = data.message.strip()
    if not new_text:
        return error_response(status_code=status.HTTP_400_BAD_REQUEST, message="Message text cannot be empty")

    message.message = new_text
    db.commit()
    db.refresh(message)

    payload = {
        "event": "message_updated",
        "data": {
            "id": message.id,
            "message": message.message,
            "updated_at": str(message.updated_at),
        },
    }
    await manager.broadcast_to_submission(submission_id, payload)

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Message updated successfully",
        data=payload["data"],
    )


# ---------------------------------------------------------------------------
# DELETE ADMIN MESSAGE
# ---------------------------------------------------------------------------

async def delete_admin_message(
    submission_id: str,
    message_id: str,
    current_admin: Admin,
    db: Session,
):
    """
    Allows staff to delete any message in the conversation (moderation power).
    Sub-admins restricted to their assigned submissions.
    Broadcasts 'message_deleted' WebSocket event.
    """
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        return error_response(status_code=status.HTTP_404_NOT_FOUND, message="Submission not found")

    is_restricted = current_admin.role in [AdminRole.SUB_ADMIN.value]
    if is_restricted and submission.assigned_to_id != current_admin.id:
        return error_response(
            status_code=status.HTTP_403_FORBIDDEN,
            message="You do not have permission to delete messages in this submission",
        )

    conversation = db.query(Conversation).filter(
        Conversation.submission_id == submission_id
    ).first()
    if not conversation:
        return error_response(status_code=status.HTTP_404_NOT_FOUND, message="No conversation found")

    message = db.query(Message).filter(
        Message.id == message_id,
        Message.conversation_id == conversation.id,
    ).first()
    if not message:
        return error_response(status_code=status.HTTP_404_NOT_FOUND, message="Message not found")

    db.delete(message)
    db.commit()

    payload = {"event": "message_deleted", "data": {"id": message_id}}
    await manager.broadcast_to_submission(submission_id, payload)

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Message deleted successfully",
        data={"id": message_id},
    )


# ---------------------------------------------------------------------------
# MARK MESSAGES AS READ (ADMIN)
# ---------------------------------------------------------------------------

async def mark_admin_messages_read(
    submission_id: str,
    current_admin: Admin,
    db: Session,
):
    """
    Marks all unread CLIENT messages in the conversation as read.
    Broadcasts 'read_receipt' WebSocket event.
    """
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        return error_response(status_code=status.HTTP_404_NOT_FOUND, message="Submission not found")

    is_restricted = current_admin.role in [AdminRole.SUB_ADMIN.value]
    if is_restricted and submission.assigned_to_id != current_admin.id:
        return error_response(
            status_code=status.HTTP_403_FORBIDDEN,
            message="You do not have permission to manage messages in this submission",
        )

    conversation = db.query(Conversation).filter(
        Conversation.submission_id == submission_id
    ).first()
    if not conversation:
        return error_response(status_code=status.HTTP_404_NOT_FOUND, message="No conversation found")

    updated_count = (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation.id,
            Message.sender_type == MessageSenderType.CLIENT.value,
            Message.is_read == False,
        )
        .update({"is_read": True})
    )
    db.commit()

    read_at = str(datetime.now(timezone.utc))
    payload = {
        "event": "read_receipt",
        "data": {
            "read_by": "staff",
            "read_by_name": f"{current_admin.first_name} {current_admin.last_name}",
            "read_at": read_at,
            "messages_marked": updated_count,
        },
    }
    await manager.broadcast_to_submission(submission_id, payload)

    return success_response(
        status_code=status.HTTP_200_OK,
        message=f"{updated_count} message(s) marked as read",
        data=payload["data"],
    )
