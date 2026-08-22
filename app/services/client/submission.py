from fastapi import status
from sqlalchemy.orm import Session
from uuid_extensions import uuid7

from app.models.clients import Client
from app.models.submissions import Submission
from app.models.chats import Conversation
from app.models.enums import SubmissionStatus
from app.schema.submission import CreateSubmission
from app.utils.custom_response import success_response, error_response


async def create_submission(data: CreateSubmission, db: Session):
    """
    Creates a client profile (if not existing), then creates a
    submission record, opens a conversation, and returns
    a secure access token for the client to track their request.
    """

    email_lower = data.email.lower().strip()

    # --- Step 1: Look up existing client or create a new one ---
    client = db.query(Client).filter(Client.email == email_lower).first()

    if not client:
        client = Client(
            first_name=data.first_name.strip(),
            last_name=data.last_name.strip(),
            email=email_lower,
            phone=data.phone,
        )
        db.add(client)
        db.flush()  # Flush to get client.id before committing

    # --- Step 2: Create the Submission record ---
    access_token = str(uuid7())

    submission = Submission(
        client_id=client.id,
        target_position=data.target_position.strip(),
        job_description=data.job_description,
        existing_cv_url=data.existing_cv_url,
        raw_data=data.raw_data.model_dump(),
        status=SubmissionStatus.NEW.value,
        assigned_to_id=None,
        access_token=access_token,
    )
    db.add(submission)
    db.flush()  # Flush to get submission.id before creating conversation

    # --- Step 3: Automatically open a conversation for this submission ---
    conversation = Conversation(submission_id=submission.id)
    db.add(conversation)

    db.commit()
    db.refresh(submission)

    return success_response(
        status_code=status.HTTP_201_CREATED,
        message="Submission created successfully. Use your access token to track this request.",
        data={
            "submission_id": submission.id,
            "access_token": submission.access_token,
            "status": submission.status,
            "client": {
                "id": client.id,
                "first_name": client.first_name,
                "last_name": client.last_name,
                "email": client.email,
            },
        },
    )


async def get_submission_status(submission_id: str, access_token: str, db: Session):
    """
    Allows a client to check the status of their submission
    using their submission_id and secret access_token.
    """

    submission = db.query(Submission).filter(
        Submission.id == submission_id,
        Submission.access_token == access_token,
    ).first()

    if not submission:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Submission not found or access token is invalid",
        )

    client = submission.client
    assigned_to = submission.assigned_to

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Submission fetched successfully",
        data={
            "submission_id": submission.id,
            "status": submission.status,
            "target_position": submission.target_position,
            "created_at": str(submission.created_at),
            "updated_at": str(submission.updated_at),
            "client": {
                "first_name": client.first_name,
                "last_name": client.last_name,
                "email": client.email,
            },
            "assigned_to": {
                "first_name": assigned_to.first_name,
                "last_name": assigned_to.last_name,
            } if assigned_to else None,
        },
    )
