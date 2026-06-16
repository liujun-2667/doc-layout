from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
import os
import shutil

from app.database import get_db
from app.services.task_service import TaskService
from app.schemas import TaskResponse, TaskListResponse
from app.config import settings
from app.worker import enqueue_task

router = APIRouter()


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    service = TaskService(db)
    tasks = service.list_tasks(skip=skip, limit=limit)
    return {
        "tasks": tasks,
        "total": len(tasks),
    }


@router.post("", response_model=TaskResponse)
async def create_task(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="未提供文件")

    ext = os.path.splitext(file.filename)[1].lower()
    allowed_extensions = {
        ".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp"
    }
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式。支持的格式: {', '.join(allowed_extensions)}"
        )

    service = TaskService(db)
    task = service.create_task(file.filename)

    upload_dir = service.get_task_upload_dir(task.id)
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    enqueue_task(task.id, file_path)

    return task


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    db: Session = Depends(get_db),
):
    service = TaskService(db)
    task = service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@router.post("/{task_id}/retry", response_model=TaskResponse)
async def retry_task(
    task_id: str,
    db: Session = Depends(get_db),
):
    service = TaskService(db)
    task = service.retry_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在或无法重试")

    upload_dir = service.get_task_upload_dir(task.id)
    files = os.listdir(upload_dir)
    if files:
        file_path = os.path.join(upload_dir, files[0])
        enqueue_task(task.id, file_path)

    return task


@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    db: Session = Depends(get_db),
):
    from app.models import Task
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    service = TaskService(db)

    task_dir = service.get_task_upload_dir(task_id)
    result_dir = service.get_task_result_dir(task_id)

    if os.path.exists(task_dir):
        shutil.rmtree(task_dir, ignore_errors=True)
    if os.path.exists(result_dir):
        shutil.rmtree(result_dir, ignore_errors=True)

    db.delete(task)
    db.commit()

    return {"message": "任务已删除"}
