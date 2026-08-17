from typing import Literal, Optional

from pydantic import BaseModel, Field

Status = Literal["pending", "in_progress", "done"]


class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)


class TaskCreate(TaskBase):
    status: Status = "pending"


class TaskUpdate(TaskBase):
    status: Status


class Task(TaskBase):
    id: int
    status: Status
    created_at: str
    updated_at: str


class TaskListResponse(BaseModel):
    items: list[Task]
    page: int
    page_size: int
    total: int
    total_pages: int
