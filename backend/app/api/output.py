from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os

from app.database import get_db
from app.services.task_service import TaskService
from app.config import settings

router = APIRouter()


@router.get("/{task_id}")
async def get_output(
    task_id: str,
    format: str = Query("json", pattern="^(json|html|markdown)$"),
    db: Session = Depends(get_db),
):
    service = TaskService(db)
    task = service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status != "completed":
        raise HTTPException(status_code=400, detail="任务尚未完成")

    try:
        output_path = service.generate_output(task_id, format)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not os.path.exists(output_path):
        raise HTTPException(status_code=404, detail="输出文件不存在")

    ext_map = {
        "json": "application/json",
        "html": "text/html",
        "markdown": "text/markdown",
    }

    return FileResponse(
        output_path,
        media_type=ext_map.get(format, "text/plain"),
        filename=f"output.{format.replace('markdown', 'md')}",
    )
