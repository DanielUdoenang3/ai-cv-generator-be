from typing import Optional
from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.utils.database import get_db
from app.models.admins import Admin
from app.services import get_current_admin
from app.services.admin.dashboard import get_dashboard_stats, get_recent_submissions


async def get_dashboard_stats_controller(
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Controller to retrieve scoped metrics counts for dashboard cards."""
    return await get_dashboard_stats(current_admin=current_admin, db=db)


async def get_recent_submissions_controller(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search term for client name, email, or position"),
    status: Optional[str] = Query(None, description="Filter submissions by status"),
    assigned_to_id: Optional[str] = Query(None, description="Filter submissions by assigned staff ID"),
    sort_by: str = Query("created_at", description="Field to sort by (created_at, updated_at, status, target_position)"),
    sort_order: str = Query("desc", description="Sort direction (asc, desc)"),
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Controller to query a paginated, sorted, and filtered list of recent submissions."""
    return await get_recent_submissions(
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
