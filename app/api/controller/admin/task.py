from typing import Optional
from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.utils.database import get_db
from app.models.admins import Admin
from app.services import get_current_admin
from app.schema.task import TaskCreate, TaskUpdate
from app.services.admin.task import (
    get_tasks_list,
    create_task,
    get_task_by_id,
    update_task,
    delete_task,
)


async def get_tasks_controller(
    view_tab: Optional[str] = Query("all", description="View tab: all, my_tasks, high_priority, overdue"),
    status: Optional[str] = Query(None, description="Filter task by status: todo, in_progress, review, done"),
    assigned_to_id: Optional[str] = Query(None, description="Filter by assigned staff ID, 'me', or 'unassigned'"),
    priority: Optional[str] = Query(None, description="Filter by priority: low, normal, high"),
    search: Optional[str] = Query(None, description="Search task title, description, or submission reference ID"),
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Controller to query tasks list with metrics overview."""
    return await get_tasks_list(
        db=db,
        current_admin=current_admin,
        view_tab=view_tab,
        task_status=status,
        assigned_to_id=assigned_to_id,
        priority=priority,
        search=search,
    )


async def create_task_controller(
    payload: TaskCreate,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Controller to create a new task card."""
    return await create_task(data=payload, current_admin=current_admin, db=db)


async def get_task_by_id_controller(
    task_id: str,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Controller to fetch single task details."""
    return await get_task_by_id(task_id=task_id, current_admin=current_admin, db=db)


async def update_task_controller(
    task_id: str,
    payload: TaskUpdate,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Controller to update task details or move status column."""
    return await update_task(
        task_id=task_id, data=payload, current_admin=current_admin, db=db
    )


async def delete_task_controller(
    task_id: str,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Controller to delete a task card."""
    return await delete_task(task_id=task_id, current_admin=current_admin, db=db)
