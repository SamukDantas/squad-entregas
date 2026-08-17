from typing import Optional

from fastapi import APIRouter, HTTPException, Query

import db
from schemas import Status, Task, TaskCreate, TaskListResponse, TaskUpdate

router = APIRouter()


@router.get("/tasks", response_model=TaskListResponse)
def list_tasks(
    status: Optional[Status] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
):
    items, total = db.list_tasks(status=status, page=page, page_size=page_size)
    total_pages = (total + page_size - 1) // page_size if total else 0
    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
    }


@router.get("/tasks/{task_id}", response_model=Task)
def get_task(task_id: int):
    task = db.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/tasks", response_model=Task, status_code=201)
def create_task(payload: TaskCreate):
    return db.create_task(payload.title, payload.description, payload.status)


@router.put("/tasks/{task_id}", response_model=Task)
def update_task(task_id: int, payload: TaskUpdate):
    task = db.update_task(task_id, payload.title, payload.description, payload.status)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    if not db.delete_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    return None
