from datetime import datetime, timezone
from typing import Optional, List, Any

from fastapi import status, UploadFile
from sqlalchemy.orm import Session

from app.models.chats import Conversation, Message
from app.models.submissions import Submission
from app.models.enums import MessageSenderType
from app.schema.chat import MessageCreate, MessageEdit
from app.utils.cloudinary import upload_multiple_files_to_cloudinary
from app.utils.custom_response import success_response, error_response
from app.utils.websocket_manager import manager


def _validate_client_access(
    submission_id: str,
    access_token: str,
    db: Session,
) -> Submission | None:
    """
    Internal helper — validates that the provided access_token
    belongs to the specified submission. Returns the Submission
    object if valid, otherwise None.
    """
    return db.query(Submission).filter(
        Submission.id == submission_id,
        Submission.access_token == access_token,
    ).first()


def _get_conversation(submission_id: str, db: Session) -> Conversation | None:
    return db.query(Conversation).filter(
        Conversation.submission_id == submission_id
    ).first()


# ---------------------------------------------------------------------------
# GET MESSAGES
# ---------------------------------------------------------------------------

async def get_messages(submission_id: str, access_token: str, db: Session):
    """
    Returns the full message history for a submission's conversation.
    Validates the client access token before returning any data.
    """
    submission = _validate_client_access(submission_id, access_token, db)
    if not submission:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Submission not found or access token is invalid",
        )

    conversation = _get_conversation(submission_id, db)
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
            "messages": [
                {
                    "id": msg.id,
                    "sender_type": msg.sender_type,
                    "sender_name": (
                        f"{msg.sender.first_name} {msg.sender.last_name}"
                        if msg.sender_type == MessageSenderType.STAFF.value and msg.sender
                        else "You"
                    ),
                    "message": msg.message,
                    "attachments": msg.attachments,
                    "is_read": msg.is_read,
                    "created_at": str(msg.created_at),
                    "updated_at": str(msg.updated_at),
                }
                for msg in messages
            ],
        },
    )


# ---------------------------------------------------------------------------
# SEND MESSAGE
# ---------------------------------------------------------------------------

async def send_message(
    submission_id: str,
    access_token: str,
    db: Session,
    message_text: Optional[str] = None,
    attachments: Optional[List[Any]] = None,
    raw_files: Optional[List[UploadFile]] = None,
    data: Optional[MessageCreate] = None,
):
    """
    Allows the client to send a message in their submission's conversation.
    Supports JSON pre-uploaded attachment links AND direct raw file uploads to Cloudinary.
    Broadcasts a 'new_message' WebSocket event to all active connections for this submission.
    """
    submission = _validate_client_access(submission_id, access_token, db)
    if not submission:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Submission not found or access token is invalid",
        )

    conversation = _get_conversation(submission_id, db)
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
        sender_type=MessageSenderType.CLIENT.value,
        sender_id=None,
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
            "sender_name": "You",
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
# EDIT MESSAGE
# ---------------------------------------------------------------------------

async def edit_message(
    submission_id: str,
    message_id: str,
    access_token: str,
    data: MessageEdit,
    db: Session,
):
    """
    Allows the client to edit one of their own messages.
    Broadcasts a 'message_updated' WebSocket event.
    """
    submission = _validate_client_access(submission_id, access_token, db)
    if not submission:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Submission not found or access token is invalid",
        )

    conversation = _get_conversation(submission_id, db)
    if not conversation:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="No conversation found for this submission",
        )

    message = db.query(Message).filter(
        Message.id == message_id,
        Message.conversation_id == conversation.id,
        Message.sender_type == MessageSenderType.CLIENT.value,
    ).first()

    if not message:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Message not found or you do not have permission to edit it",
        )

    new_text = data.message.strip()
    if not new_text:
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Message text cannot be empty",
        )

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
# DELETE MESSAGE
# ---------------------------------------------------------------------------

async def delete_message(
    submission_id: str,
    message_id: str,
    access_token: str,
    db: Session,
):
    """
    Allows the client to delete one of their own messages.
    Broadcasts a 'message_deleted' WebSocket event.
    """
    submission = _validate_client_access(submission_id, access_token, db)
    if not submission:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Submission not found or access token is invalid",
        )

    conversation = _get_conversation(submission_id, db)
    if not conversation:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="No conversation found for this submission",
        )

    message = db.query(Message).filter(
        Message.id == message_id,
        Message.conversation_id == conversation.id,
        Message.sender_type == MessageSenderType.CLIENT.value,
    ).first()

    if not message:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Message not found or you do not have permission to delete it",
        )

    db.delete(message)
    db.commit()

    payload = {
        "event": "message_deleted",
        "data": {"id": message_id},
    }
    await manager.broadcast_to_submission(submission_id, payload)

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Message deleted successfully",
        data={"id": message_id},
    )


# ---------------------------------------------------------------------------
# MARK MESSAGES AS READ
# ---------------------------------------------------------------------------

async def mark_messages_read(
    submission_id: str,
    access_token: str,
    db: Session,
):
    """
    Marks all unread STAFF messages in the conversation as read (client is reading).
    Broadcasts a 'read_receipt' WebSocket event.
    """
    submission = _validate_client_access(submission_id, access_token, db)
    if not submission:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Submission not found or access token is invalid",
        )

    conversation = _get_conversation(submission_id, db)
    if not conversation:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="No conversation found for this submission",
        )

    updated_count = (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation.id,
            Message.sender_type == MessageSenderType.STAFF.value,
            Message.is_read == False,
        )
        .update({"is_read": True})
    )
    db.commit()

    read_at = str(datetime.now(timezone.utc))
    payload = {
        "event": "read_receipt",
        "data": {
            "read_by": "client",
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
