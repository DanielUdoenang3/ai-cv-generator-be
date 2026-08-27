from datetime import datetime, timezone
from typing import Optional
from fastapi import status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.tasks import Task
from app.models.submissions import Submission
from app.models.admins import Admin
from app.models.clients import Client
from app.models.enums import TaskPriority, TaskStatus
from app.schema.task import TaskCreate, TaskUpdate
from app.utils.custom_response import success_response, error_response


def _format_task_data(task: Task) -> dict:
    """Helper to convert Task model to UI card response dict"""
    submission_summary = None
    if task.submission:
        client_name = None
        if task.submission.client:
            client_name = f"{task.submission.client.first_name} {task.submission.client.last_name}".strip()
        submission_summary = {
            "id": task.submission.id,
            "reference_id": task.submission.reference_id,
            "target_position": task.submission.target_position,
            "client_name": client_name,
        }

    assignee_summary = None
    if task.assigned_to:
        assignee_summary = {
            "id": task.assigned_to.id,
            "first_name": task.assigned_to.first_name,
            "last_name": task.assigned_to.last_name,
            "role": task.assigned_to.role,
        }

    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "priority": task.priority,
        "status": task.status,
        "deadline": task.deadline,
        "submission": submission_summary,
        "assigned_to": assignee_summary,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }


async def get_tasks_list(
    db: Session,
    current_admin: Admin,
    view_tab: Optional[str] = "all",
    task_status: Optional[str] = None,
    assigned_to_id: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None,
):
    """
    Fetch all tasks with Kanban overview statistics and filtering support.
    Stats:
    - total_tasks: Total tasks count
    - my_tasks: Count assigned to current admin
    - overdue: Deadline < UTC now and status != 'done'
    - high_priority: Count where priority == 'high'
    - Column breakdown: todo_count, in_progress_count, review_count, done_count
    """
    now = datetime.now(timezone.utc)

    # 1. System-wide / Scoped Metrics
    total_tasks = db.query(Task).count()
    my_tasks = db.query(Task).filter(Task.assigned_to_id == current_admin.id).count()
    overdue_count = (
        db.query(Task)
        .filter(
            Task.deadline.isnot(None),
            Task.deadline < now,
            Task.status != TaskStatus.DONE.value,
        )
        .count()
    )
    high_priority_count = (
        db.query(Task).filter(Task.priority == TaskPriority.HIGH.value).count()
    )

    todo_count = db.query(Task).filter(Task.status == TaskStatus.TODO.value).count()
    in_progress_count = (
        db.query(Task).filter(Task.status == TaskStatus.IN_PROGRESS.value).count()
    )
    review_count = (
        db.query(Task).filter(Task.status == TaskStatus.REVIEW.value).count()
    )
    done_count = db.query(Task).filter(Task.status == TaskStatus.DONE.value).count()

    metrics = {
        "total_tasks": total_tasks,
        "my_tasks": my_tasks,
        "overdue": overdue_count,
        "high_priority": high_priority_count,
        "todo_count": todo_count,
        "in_progress_count": in_progress_count,
        "review_count": review_count,
        "done_count": done_count,
    }

    # 2. Build filtered Query
    query = (
        db.query(Task)
        .outerjoin(Submission, Task.submission_id == Submission.id)
        .outerjoin(Client, Submission.client_id == Client.id)
    )

    # View tab filtering
    if view_tab == "my_tasks":
        query = query.filter(Task.assigned_to_id == current_admin.id)
    elif view_tab == "high_priority":
        query = query.filter(Task.priority == TaskPriority.HIGH.value)
    elif view_tab == "overdue":
        query = query.filter(
            Task.deadline.isnot(None),
            Task.deadline < now,
            Task.status != TaskStatus.DONE.value,
        )

    # Query param filters
    if task_status:
        query = query.filter(Task.status == task_status)

    if assigned_to_id:
        if assigned_to_id == "me":
            query = query.filter(Task.assigned_to_id == current_admin.id)
        elif assigned_to_id == "unassigned":
            query = query.filter(Task.assigned_to_id.is_(None))
        else:
            query = query.filter(Task.assigned_to_id == assigned_to_id)

    if priority:
        query = query.filter(Task.priority == priority)

    if search:
        search_fmt = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Task.title.ilike(search_fmt),
                Task.description.ilike(search_fmt),
                Submission.reference_id.ilike(search_fmt),
                Client.first_name.ilike(search_fmt),
                Client.last_name.ilike(search_fmt),
            )
        )

    tasks = query.order_by(Task.created_at.desc()).all()
    tasks_formatted = [_format_task_data(t) for t in tasks]

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Tasks fetched successfully",
        data={"stats": metrics, "tasks": tasks_formatted},
    )


async def create_task(data: TaskCreate, current_admin: Admin, db: Session):
    """
    Create a new task card.
    Optionally link to submission_id and assigned_to_id.
    """
    if not data.title or not data.title.strip():
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Task title is required",
        )

    if data.submission_id:
        sub = db.query(Submission).filter(Submission.id == data.submission_id).first()
        if not sub:
            return error_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Linked submission not found",
            )

    if data.assigned_to_id:
        assignee = db.query(Admin).filter(Admin.id == data.assigned_to_id).first()
        if not assignee:
            return error_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Assigned staff member not found",
            )

    new_task = Task(
        title=data.title.strip(),
        description=data.description.strip() if data.description else None,
        submission_id=data.submission_id,
        assigned_to_id=data.assigned_to_id,
        priority=data.priority,
        status=data.status,
        deadline=data.deadline,
    )

    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    return success_response(
        status_code=status.HTTP_201_CREATED,
        message="Task created successfully",
        data=_format_task_data(new_task),
    )


async def get_task_by_id(task_id: str, current_admin: Admin, db: Session):
    """
    Fetch single task details.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Task not found",
        )

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Task fetched successfully",
        data=_format_task_data(task),
    )


async def update_task(
    task_id: str, data: TaskUpdate, current_admin: Admin, db: Session
):
    """
    Update task details (title, description, status column, priority, assignee, deadline).
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Task not found",
        )

    if data.title is not None:
        if not data.title.strip():
            return error_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Task title cannot be empty",
            )
        task.title = data.title.strip()

    if data.description is not None:
        task.description = data.description.strip() if data.description else None

    if data.submission_id is not None:
        if data.submission_id:
            sub = (
                db.query(Submission)
                .filter(Submission.id == data.submission_id)
                .first()
            )
            if not sub:
                return error_response(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message="Linked submission not found",
                )
            task.submission_id = data.submission_id
        else:
            task.submission_id = None

    if data.assigned_to_id is not None:
        if data.assigned_to_id:
            assignee = db.query(Admin).filter(Admin.id == data.assigned_to_id).first()
            if not assignee:
                return error_response(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message="Assigned staff member not found",
                )
            task.assigned_to_id = data.assigned_to_id
        else:
            task.assigned_to_id = None

    if data.priority is not None:
        task.priority = data.priority

    if data.status is not None:
        task.status = data.status

    if data.deadline is not None:
        task.deadline = data.deadline

    db.commit()
    db.refresh(task)

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Task updated successfully",
        data=_format_task_data(task),
    )


async def delete_task(task_id: str, current_admin: Admin, db: Session):
    """
    Delete task card.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Task not found",
        )

    db.delete(task)
    db.commit()

    return success_response(
        status_code=status.HTTP_200_OK,
        message="Task deleted successfully",
    )
