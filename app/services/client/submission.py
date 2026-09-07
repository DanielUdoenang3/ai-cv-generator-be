"""
services/client/submission.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Public-facing submission service.

create_submission   — Creates (or updates) a client profile from the full
                      intake form and opens a new submission + conversation.
get_submission_status — Lets a client poll their submission by token.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import status
from sqlalchemy.orm import Session
from uuid_extensions import uuid7

from app.models.activities import SubmissionActivity
from app.models.chats import Conversation
from app.models.clients import Client
from app.models.documents import Document
from app.models.enums import SubmissionStatus
from app.models.submissions import Submission
from app.schema.submission import CreateSubmission
from app.utils.custom_response import error_response, success_response


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _apply_client_fields(client: Client, data: CreateSubmission) -> None:
    """
    Write every intake field from ``CreateSubmission`` onto a Client ORM object.
    Called both when creating a new client and when updating an existing one
    (re-submission with the same email updates profile details in place).
    """
    # ── Core identity ─────────────────────────────────────────────────────
    client.first_name  = data.first_name.strip()
    client.middle_name = data.middle_name.strip() if data.middle_name else None
    client.last_name   = data.last_name.strip()
    client.date_of_birth = data.date_of_birth  # date | None

    # ── Contact ───────────────────────────────────────────────────────────
    client.phone        = data.phone
    client.address_line = data.address_line
    client.city         = data.city
    client.state        = data.state
    client.country      = data.country
    client.zip_code     = data.zip_code

    # ── Online presence ───────────────────────────────────────────────────
    client.linkedin_url  = data.linkedin_url
    client.portfolio_url = data.portfolio_url

    # ── Resume file ───────────────────────────────────────────────────────
    if data.resume_file_url:
        client.resume_file_url  = data.resume_file_url
        client.resume_file_name = data.resume_file_name

    # ── Job preferences ───────────────────────────────────────────────────
    client.desired_job_titles        = data.desired_job_titles
    client.preferred_work_arrangement = (
        data.preferred_work_arrangement.value
        if data.preferred_work_arrangement else None
    )
    client.expected_salary_range = data.expected_salary_range
    client.available_start_date  = data.available_start_date
    client.companies_to_exclude  = data.companies_to_exclude

    # ── Work authorisation ────────────────────────────────────────────────
    client.security_clearance = (
        data.security_clearance.value if data.security_clearance else None
    )
    client.citizenship_status        = data.citizenship_status
    client.visa_sponsorship_required = (
        data.visa_sponsorship_required.value
        if data.visa_sponsorship_required else None
    )
    client.non_compete_obligations = data.non_compete_obligations

    # ── Professional references (serialise Pydantic models → plain dicts) ─
    if data.professional_references is not None:
        client.professional_references = [
            ref.model_dump() for ref in data.professional_references
        ]

    # ── Demographics (EEO — voluntary) ───────────────────────────────────
    client.gender = data.gender.value if data.gender else None
    client.sexual_orientation = (
        data.sexual_orientation.value if data.sexual_orientation else None
    )
    client.race_ethnicity  = data.race_ethnicity.value  if data.race_ethnicity  else None
    client.veteran_status  = data.veteran_status.value  if data.veteran_status  else None
    client.has_disability  = data.has_disability.value  if data.has_disability  else None

    # ── Notes ─────────────────────────────────────────────────────────────
    client.notes = data.notes


def _serialize_client(client: Client) -> dict:
    """Return a concise client dict suitable for API responses."""
    return {
        "id":         client.id,
        "first_name": client.first_name,
        "middle_name": client.middle_name,
        "last_name":  client.last_name,
        "email":      client.email,
        "phone":      client.phone,
        "city":       client.city,
        "state":      client.state,
        "country":    client.country,
        "linkedin_url":  client.linkedin_url,
        "portfolio_url": client.portfolio_url,
        "resume_file_url":  client.resume_file_url,
        "resume_file_name": client.resume_file_name,
        "desired_job_titles":         client.desired_job_titles,
        "preferred_work_arrangement": client.preferred_work_arrangement,
        "expected_salary_range":      client.expected_salary_range,
        "available_start_date":       str(client.available_start_date) if client.available_start_date else None,
        "citizenship_status":         client.citizenship_status,
        "visa_sponsorship_required":  client.visa_sponsorship_required,
        "veteran_status":             client.veteran_status,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Public service functions
# ─────────────────────────────────────────────────────────────────────────────

async def create_submission(data: CreateSubmission, db: Session):
    """
    Full intake pipeline:

    1. Upsert Client record (create on first visit; update fields on return).
    2. Create Submission with reference ID + access token.
    3. Open a Conversation for the submission.
    4. Log an initial SubmissionActivity.
    5. Return access token so the client can poll their status.
    """
    email_lower = data.email.lower().strip()

    # ── 1. Upsert client ──────────────────────────────────────────────────
    client = db.query(Client).filter(Client.email == email_lower).first()

    if client:
        # Update profile with the latest submitted data
        _apply_client_fields(client, data)
    else:
        client = Client(email=email_lower)
        _apply_client_fields(client, data)
        db.add(client)

    db.flush()  # obtain client.id before referencing it in Submission

    # ── 2. Create submission ──────────────────────────────────────────────
    access_token = str(uuid7())

    current_year = datetime.now(timezone.utc).year
    prefix = f"SUB-{current_year}-"
    count = (
        db.query(Submission)
        .filter(Submission.reference_id.like(f"{prefix}%"))
        .count()
    )
    reference_id = f"{prefix}{str(count + 1).zfill(3)}"

    submission = Submission(
        client_id=client.id,
        reference_id=reference_id,
        target_position=data.target_position.strip() if data.target_position else None,
        target_company=data.target_company.strip() if data.target_company else None,
        priority=data.priority or "normal",
        job_description=data.job_description,
        existing_cv_url=data.resume_file_url,   # mirror the uploaded resume URL
        raw_data=data.raw_data.model_dump() if data.raw_data else None,
        status=SubmissionStatus.NEW.value,
        assigned_to_id=None,
        access_token=access_token,
    )
    db.add(submission)
    db.flush()  # obtain submission.id before creating conversation

    # ── 3. Open conversation ──────────────────────────────────────────────
    conversation = Conversation(submission_id=submission.id)
    db.add(conversation)

    # ── 4. Log creation activity ──────────────────────────────────────────
    activity = SubmissionActivity(
        submission_id=submission.id,
        activity_type="submission_created",
        title="Submission Created",
        description="Client submitted intake form",
    )
    db.add(activity)

    db.commit()
    db.refresh(submission)

    return success_response(
        status_code=status.HTTP_201_CREATED,
        message=(
            "Submission created successfully. "
            "Use your access token to track this request."
        ),
        data={
            "submission_id":  submission.id,
            "reference_id":   submission.reference_id,
            "access_token":   submission.access_token,
            "status":         submission.status,
            "client":         _serialize_client(client),
        },
    )


async def get_submission_status(
    submission_id: str,
    access_token: str,
    db: Session,
):
    """
    Token-gated status check for the client-facing portal.
    Returns submission state, assigned staff name, and any generated documents.
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

    client      = submission.client
    assigned_to = submission.assigned_to

    docs = (
        db.query(Document)
        .filter(Document.submission_id == submission.id)
        .order_by(Document.document_kind, Document.file_type, Document.version)
        .all()
    )

    documents_list = [
        {
            "id":            d.id,
            "file_name":     d.file_name,
            "file_url":      d.file_url,
            "file_type":     d.file_type,
            "document_kind": d.document_kind,
            "version":       d.version,
            "created_at":    str(d.created_at),
        }
        for d in docs
    ]

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Submission fetched successfully",
        data={
            "submission_id":    submission.id,
            "reference_id":     submission.reference_id,
            "status":           submission.status,
            "target_position":  submission.target_position,
            "created_at":       str(submission.created_at),
            "updated_at":       str(submission.updated_at),
            "client": {
                "first_name":  client.first_name,
                "last_name":   client.last_name,
                "email":       client.email,
                "phone":       client.phone,
            } if client else None,
            "assigned_to": {
                "first_name": assigned_to.first_name,
                "last_name":  assigned_to.last_name,
            } if assigned_to else None,
            "documents": documents_list,
        },
    )
