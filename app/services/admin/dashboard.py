"""
services/admin/dashboard.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Dashboard data service.

Super-admin  → full stats (new / in-progress / completed / active chats)
              + recent-submissions list with all filters.

Sub-admin    → clean assigned-client list only.
              No status counters, no unrelated clutter.
"""

from __future__ import annotations

from typing import Optional

from fastapi import status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.admins import Admin
from app.models.chats import Conversation, Message
from app.models.clients import Client
from app.models.enums import AdminRole
from app.models.submissions import Submission
from app.utils.custom_response import success_response


# ─────────────────────────────────────────────────────────────────────────────
# Serialiser
# ─────────────────────────────────────────────────────────────────────────────

def _serialize_submission(submission: Submission) -> dict:
    """Compact submission dict for dashboard list views."""
    client      = submission.client
    assigned_to = submission.assigned_to
    return {
        "id":             submission.id,
        "reference_id":   submission.reference_id,
        "target_position": submission.target_position,
        "target_company":  submission.target_company,
        "priority":        submission.priority,
        "status":          submission.status,
        "created_at":      submission.created_at,
        "updated_at":      submission.updated_at,
        "client": {
            "id":         client.id,
            "first_name": client.first_name,
            "last_name":  client.last_name,
            "email":      client.email,
            "phone":      client.phone,
            "city":       client.city,
            "state":      client.state,
            "country":    client.country,
            "linkedin_url":         client.linkedin_url,
            "desired_job_titles":   client.desired_job_titles,
            "preferred_work_arrangement": client.preferred_work_arrangement,
            "resume_file_url":      client.resume_file_url,
        } if client else None,
        "assigned_to": {
            "id":         assigned_to.id,
            "first_name": assigned_to.first_name,
            "last_name":  assigned_to.last_name,
            "role":       assigned_to.role,
        } if assigned_to else None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Stats  (super-admin only)
# ─────────────────────────────────────────────────────────────────────────────

async def get_dashboard_stats(current_admin: Admin, db: Session):
    """
    Returns overview metric counts for the super-admin dashboard cards.
    Sub-admins receive an empty stats block — they have no stats dashboard.
    """
    is_super = current_admin.role == AdminRole.SUPER_ADMIN.value

    if not is_super:
        # Sub-admins do not have a stats dashboard; return a clean empty object
        # so the frontend can safely destructure without guarding every field.
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Dashboard stats not available for this role",
            data={},
        )

    new_count = (
        db.query(Submission).filter(Submission.status == "new").count()
    )
    in_progress_count = (
        db.query(Submission).filter(Submission.status == "in_progress").count()
    )
    completed_count = (
        db.query(Submission).filter(Submission.status == "completed").count()
    )
    active_chats_count = (
        db.query(Conversation)
        .join(Submission, Conversation.submission_id == Submission.id)
        .join(Message,    Message.conversation_id   == Conversation.id)
        .filter(Submission.status.notin_(["completed", "rejected"]))
        .distinct()
        .count()
    )

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Dashboard stats fetched successfully",
        data={
            "new_requests": new_count,
            "in_progress":  in_progress_count,
            "completed":    completed_count,
            "active_chats": active_chats_count,
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# Assigned-client list  (both roles — scoped by RBAC)
# ─────────────────────────────────────────────────────────────────────────────

async def get_recent_submissions(
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
    Paginated, filterable submission list.

    Super-admin  → sees all submissions; can filter by assigned_to_id.
    Sub-admin    → sees only submissions assigned to them; all other filters
                   still work but are silently scoped to their own records.
    """
    is_super = current_admin.role == AdminRole.SUPER_ADMIN.value

    query = db.query(Submission).outerjoin(Client, Submission.client_id == Client.id)

    # ── RBAC scoping ──────────────────────────────────────────────────────
    if not is_super:
        query = query.filter(Submission.assigned_to_id == current_admin.id)
    else:
        if assigned_to_id:
            if assigned_to_id.lower() == "unassigned":
                query = query.filter(Submission.assigned_to_id.is_(None))
            else:
                query = query.filter(Submission.assigned_to_id == assigned_to_id)

    # ── Search ────────────────────────────────────────────────────────────
    if search:
        pat = f"%{search}%"
        query = query.filter(
            or_(
                Client.first_name.ilike(pat),
                Client.last_name.ilike(pat),
                Client.email.ilike(pat),
                Submission.target_position.ilike(pat),
                Submission.target_company.ilike(pat),
                Submission.reference_id.ilike(pat),
            )
        )

    # ── Status filter ─────────────────────────────────────────────────────
    if status_filter:
        query = query.filter(Submission.status == status_filter)

    # ── Sort ──────────────────────────────────────────────────────────────
    _sort_map = {
        "created_at":    Submission.created_at,
        "updated_at":    Submission.updated_at,
        "status":        Submission.status,
        "target_position": Submission.target_position,
        "reference_id":  Submission.reference_id,
        "priority":      Submission.priority,
    }
    col = _sort_map.get(sort_by, Submission.created_at)
    query = query.order_by(col.asc() if sort_order.lower() == "asc" else col.desc())

    # ── Pagination ────────────────────────────────────────────────────────
    total  = query.count()
    pages  = (total + limit - 1) // limit if total else 0
    offset = (page - 1) * limit

    submissions = query.offset(offset).limit(limit).all()

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Submissions fetched successfully",
        data={
            "total":       total,
            "page":        page,
            "limit":       limit,
            "pages":       pages,
            "submissions": [_serialize_submission(s) for s in submissions],
        },
    )
