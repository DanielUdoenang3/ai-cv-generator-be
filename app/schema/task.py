from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional
from datetime import datetime
from app.models.enums import TaskPriority, TaskStatus

class TaskSubmissionSummary(BaseModel):
    id: str
    reference_id: str
    target_position: str
    client_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TaskAssigneeSummary(BaseModel):
    id: str
    first_name: str
    last_name: str
    role: str

    model_config = ConfigDict(from_attributes=True)


class TaskCreate(BaseModel):
    title: str = Field(..., description="Task title")
    description: Optional[str] = Field(None, description="Task details / notes")
    submission_id: Optional[str] = Field(None, description="Linked submission UUID")
    assigned_to_id: Optional[str] = Field(None, description="Assigned staff/admin UUID")
    priority: str = Field(default=TaskPriority.NORMAL.value, description="low, normal, high")
    status: str = Field(default=TaskStatus.TODO.value, description="todo, in_progress, review, done")
    deadline: Optional[datetime] = Field(None, description="Due date timestamp")


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    submission_id: Optional[str] = None
    assigned_to_id: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    deadline: Optional[datetime] = None


class TaskResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    priority: str
    status: str
    deadline: Optional[datetime] = None
    submission: Optional[TaskSubmissionSummary] = None
    assigned_to: Optional[TaskAssigneeSummary] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskMetrics(BaseModel):
    total_tasks: int = 0
    my_tasks: int = 0
    overdue: int = 0
    high_priority: int = 0
    todo_count: int = 0
    in_progress_count: int = 0
    review_count: int = 0
    done_count: int = 0


class TaskListResponse(BaseModel):
    stats: TaskMetrics
    tasks: List[TaskResponse]
