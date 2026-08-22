from typing import Optional, List
from fastapi import status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.admins import Admin
from app.models.submissions import Submission
from app.models.chats import Conversation, Message
from app.models.clients import Client
from app.models.enums import AdminRole
from app.utils.custom_response import success_response, error_response


def _serialize_recent_submission(submission: Submission) -> dict:
    """Internal helper to serialize submission object for dashboard table."""
    client = submission.client
    assigned_to = submission.assigned_to
    return {
        "id": submission.id,
        "reference_id": submission.reference_id,
        "target_position": submission.target_position,
        "target_company": submission.target_company,
        "priority": submission.priority,
        "status": submission.status,
        "created_at": submission.created_at,
        "updated_at": submission.updated_at,
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


async def get_dashboard_stats(current_admin: Admin, db: Session):
    """
    Computes dashboard analytics counts:
    - new_requests
    - in_progress
    - completed
    - active_chats (linked to active submissions, with >=1 message)
    
    If the caller is a Sub-Admin, counts are scoped to their assigned submissions.
    """
    is_super = current_admin.role == AdminRole.SUPER_ADMIN.value

    # Base queries
    new_query = db.query(Submission).filter(Submission.status == "new")
    in_progress_query = db.query(Submission).filter(Submission.status == "in_progress")
    completed_query = db.query(Submission).filter(Submission.status == "completed")

    active_chats_query = (
        db.query(Conversation)
        .join(Submission, Conversation.submission_id == Submission.id)
        .join(Message, Message.conversation_id == Conversation.id)
        .filter(Submission.status.notin_(["completed", "rejected"]))
        .distinct()
    )

    # Scoping for sub-admins
    if not is_super:
        new_query = new_query.filter(Submission.assigned_to_id == current_admin.id)
        in_progress_query = in_progress_query.filter(Submission.assigned_to_id == current_admin.id)
        completed_query = completed_query.filter(Submission.assigned_to_id == current_admin.id)
        active_chats_query = active_chats_query.filter(Submission.assigned_to_id == current_admin.id)

    new_count = new_query.count()
    in_progress_count = in_progress_query.count()
    completed_count = completed_query.count()
    active_chats_count = active_chats_query.count()

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Dashboard stats fetched successfully",
        data={
            "new_requests": new_count,
            "in_progress": in_progress_count,
            "completed": completed_count,
            "active_chats": active_chats_count,
        }
    )


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
    Returns a paginated, filterable, and sortable list of submissions.
    Supports search query matching client details & target position.
    Respects RBAC (Sub-admins only see their assigned submissions).
    """
    is_super = current_admin.role == AdminRole.SUPER_ADMIN.value

    # Base query joining client
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
        message="Recent submissions fetched successfully",
        data={
            "total": total,
            "page": page,
            "limit": limit,
            "pages": pages,
            "submissions": [_serialize_recent_submission(s) for s in submissions]
        }
    )
