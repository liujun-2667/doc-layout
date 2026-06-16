from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from app.database import get_db
from app.models import Task
from app.schemas import (
    LayoutTemplateResponse,
    LayoutTemplateCreate,
    LayoutTemplateUpdate,
    TemplateListResponse,
    TemplateVersionResponse,
    MatchResult,
    ApplyTemplateRequest,
    SaveTemplateConflictRequest,
    TemplateCorrectionHistoryResponse,
    RecordCorrectionsRequest,
    CompositeTemplateCreate,
    CompositeTemplateUpdate,
    CompositeTemplateResponse,
)
from app.services.template_service import TemplateService

router = APIRouter()


@router.get("", response_model=TemplateListResponse)
async def list_templates(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    document_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: str = Query("created_at", pattern="^(created_at|match_count)$"),
    db: Session = Depends(get_db),
):
    service = TemplateService(db)
    templates, total = service.list_templates(
        skip=skip,
        limit=limit,
        document_type=document_type,
        search=search,
        sort_by=sort_by,
    )
    composite_templates, _ = service.list_composite_templates(
        skip=skip,
        limit=limit,
        document_type=document_type,
        search=search,
        sort_by=sort_by,
    )
    return {
        "templates": templates,
        "composite_templates": composite_templates,
        "total": total + len(composite_templates),
    }


@router.post("", response_model=LayoutTemplateResponse)
async def create_template(
    template_data: LayoutTemplateCreate,
    db: Session = Depends(get_db),
):
    service = TemplateService(db)

    if service.check_name_exists(template_data.name):
        raise HTTPException(
            status_code=409,
            detail="已存在同名模板,请选择'覆盖'或'另存为新模板'",
        )

    if template_data.source_task_id:
        task = db.query(Task).filter(Task.id == template_data.source_task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="源任务不存在")
        template = service.create_template_from_task(
            name=template_data.name,
            document_types=template_data.document_types,
            description=template_data.description,
            task=task,
        )
    else:
        template = service.create_template(template_data)

    return template


@router.post("/from-task/{task_id}", response_model=LayoutTemplateResponse)
async def create_template_from_task(
    task_id: str,
    name: str = Body(..., embed=True),
    document_types: List[str] = Body(..., embed=True),
    description: Optional[str] = Body(None, embed=True),
    db: Session = Depends(get_db),
):
    service = TemplateService(db)
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if service.check_name_exists(name):
        raise HTTPException(
            status_code=409,
            detail="已存在同名模板,请选择'覆盖'或'另存为新模板'",
        )

    template = service.create_template_from_task(
        name=name,
        document_types=document_types,
        description=description,
        task=task,
    )
    return template


@router.post("/check-name")
async def check_template_name(
    name: str = Body(..., embed=True),
    exclude_id: Optional[str] = Body(None, embed=True),
    db: Session = Depends(get_db),
):
    service = TemplateService(db)
    exists = service.check_name_exists(name, exclude_id)
    return {"exists": exists}


@router.post("/resolve-conflict/{task_id}")
async def resolve_template_conflict(
    task_id: str,
    request: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):
    service = TemplateService(db)
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    name = request.get("name")
    document_types = request.get("document_types", [])
    description = request.get("description")
    conflict_request = request.get("conflict_request", {})
    action = conflict_request.get("action")
    new_name_param = conflict_request.get("new_name")

    if action == "overwrite":
        existing_template = service.get_template_by_name(name)
        if not existing_template:
            raise HTTPException(status_code=404, detail="要覆盖的模板不存在")
        template = service.overwrite_template(existing_template.id, task)
        return template

    elif action == "save_as":
        new_name = new_name_param or f"{name} (副本)"
        counter = 1
        while service.check_name_exists(new_name):
            new_name = f"{name} (副本{counter})"
            counter += 1
        template = service.create_template_from_task(
            name=new_name,
            document_types=document_types,
            description=description,
            task=task,
        )
        return template

    else:
        raise HTTPException(status_code=400, detail="无效的冲突解决方式")


@router.get("/{template_id}", response_model=LayoutTemplateResponse)
async def get_template(
    template_id: str,
    db: Session = Depends(get_db),
):
    service = TemplateService(db)
    template = service.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    return template


@router.put("/{template_id}", response_model=LayoutTemplateResponse)
async def update_template(
    template_id: str,
    update_data: LayoutTemplateUpdate,
    db: Session = Depends(get_db),
):
    service = TemplateService(db)

    if update_data.name and service.check_name_exists(update_data.name, exclude_id=template_id):
        raise HTTPException(
            status_code=409,
            detail="已存在同名模板",
        )

    template = service.update_template(template_id, update_data)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    return template


@router.delete("/{template_id}")
async def delete_template(
    template_id: str,
    db: Session = Depends(get_db),
):
    service = TemplateService(db)
    success = service.delete_template(template_id)
    if not success:
        raise HTTPException(status_code=404, detail="模板不存在")
    return {"message": "模板已删除"}


@router.get("/{template_id}/versions", response_model=List[TemplateVersionResponse])
async def list_template_versions(
    template_id: str,
    db: Session = Depends(get_db),
):
    service = TemplateService(db)
    template = service.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    return service.list_versions(template_id)


@router.post("/{template_id}/versions/{version_id}/rollback", response_model=LayoutTemplateResponse)
async def rollback_template_version(
    template_id: str,
    version_id: str,
    db: Session = Depends(get_db),
):
    service = TemplateService(db)
    template = service.rollback_to_version(template_id, version_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板或版本不存在")
    return template


@router.post("/match/{task_id}")
async def match_template_to_task(
    task_id: str,
    document_types: Optional[List[str]] = Body(None, embed=True),
    db: Session = Depends(get_db),
):
    service = TemplateService(db)
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    result = service.match_and_apply_to_task_composite_support(task, document_types)
    task.template_match_info = result
    db.commit()
    return result


@router.post("/apply/{task_id}")
async def apply_template_to_task(
    task_id: str,
    request: ApplyTemplateRequest,
    db: Session = Depends(get_db),
):
    service = TemplateService(db)
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if request.accept:
        return {"message": "已接受模板匹配结果"}
    else:
        return {"message": "已撤销模板匹配结果"}


@router.post("/accept/{task_id}/{template_id}")
async def accept_template_match(
    task_id: str,
    template_id: str,
    is_composite: bool = Query(False),
    db: Session = Depends(get_db),
):
    service = TemplateService(db)
    if is_composite:
        service.increment_composite_match_count(template_id)
    else:
        service.increment_match_count(template_id)
    return {"message": "已接受模板匹配,匹配次数已更新"}


@router.post("/{template_id}/record-corrections")
async def record_corrections(
    template_id: str,
    request: RecordCorrectionsRequest,
    db: Session = Depends(get_db),
):
    service = TemplateService(db)
    template = service.get_template(template_id)
    if not template:
        composite = service.get_composite_template(template_id)
        if not composite:
            raise HTTPException(status_code=404, detail="模板不存在")

    template_snapshot = request.page_corrections[0] if request.page_corrections else {}

    corrections = service.record_corrections_and_learn(
        template_id=template_id,
        task_id=request.task_id,
        template_snapshot=template_snapshot,
    )
    return {
        "corrections_count": len(corrections),
        "corrections": corrections,
    }


@router.get("/{template_id}/correction-history", response_model=List[TemplateCorrectionHistoryResponse])
async def get_correction_history(
    template_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    service = TemplateService(db)
    histories, total = service.list_correction_histories(
        template_id=template_id,
        skip=skip,
        limit=limit,
    )
    return histories


@router.post("/composite", response_model=CompositeTemplateResponse)
async def create_composite_template(
    template_data: CompositeTemplateCreate,
    db: Session = Depends(get_db),
):
    service = TemplateService(db)

    if service.check_name_exists(template_data.name):
        raise HTTPException(
            status_code=409,
            detail="已存在同名模板",
        )

    template = service.create_composite_template(template_data)
    return template


@router.get("/composite/{template_id}", response_model=CompositeTemplateResponse)
async def get_composite_template(
    template_id: str,
    db: Session = Depends(get_db),
):
    service = TemplateService(db)
    template = service.get_composite_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="组合模板不存在")

    for rule in template.rules:
        base_template = service.get_template(rule.base_template_id)
        if base_template:
            rule.base_template_name = base_template.name

    return template


@router.put("/composite/{template_id}", response_model=CompositeTemplateResponse)
async def update_composite_template(
    template_id: str,
    update_data: CompositeTemplateUpdate,
    db: Session = Depends(get_db),
):
    service = TemplateService(db)

    if update_data.name and service.check_name_exists(update_data.name, exclude_id=template_id):
        raise HTTPException(
            status_code=409,
            detail="已存在同名模板",
        )

    template = service.update_composite_template(template_id, update_data)
    if not template:
        raise HTTPException(status_code=404, detail="组合模板不存在")

    for rule in template.rules:
        base_template = service.get_template(rule.base_template_id)
        if base_template:
            rule.base_template_name = base_template.name

    return template


@router.delete("/composite/{template_id}")
async def delete_composite_template(
    template_id: str,
    db: Session = Depends(get_db),
):
    service = TemplateService(db)
    success = service.delete_composite_template(template_id)
    if not success:
        raise HTTPException(status_code=404, detail="组合模板不存在")
    return {"message": "组合模板已删除"}


@router.post("/composite/match/{task_id}/{template_id}")
async def match_composite_template(
    task_id: str,
    template_id: str,
    db: Session = Depends(get_db),
):
    service = TemplateService(db)
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    composite_template = service.get_composite_template(template_id)
    if not composite_template:
        raise HTTPException(status_code=404, detail="组合模板不存在")

    result = service.match_composite_template_to_task(task, composite_template)
    task.template_match_info = result
    db.commit()
    return result


@router.post("/restore/{task_id}")
async def restore_task_elements(
    task_id: str,
    snapshot: Dict[str, Any] = Body(..., embed=True),
    db: Session = Depends(get_db),
):
    service = TemplateService(db)
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    service.restore_elements_from_snapshot(task, snapshot)
    return {"message": "已恢复原始元素"}
