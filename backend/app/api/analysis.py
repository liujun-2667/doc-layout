from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import LayoutElement, Page
from app.schemas import LayoutElementResponse

router = APIRouter()


@router.put("/elements/{element_id}", response_model=LayoutElementResponse)
async def update_element(
    element_id: str,
    element_data: dict = Body(...),
    db: Session = Depends(get_db),
):
    from app.services.task_service import TaskService

    service = TaskService(db)
    element = service.update_element(element_id, element_data)
    if not element:
        raise HTTPException(status_code=404, detail="元素不存在")
    return element


@router.delete("/elements/{element_id}")
async def delete_element(
    element_id: str,
    db: Session = Depends(get_db),
):
    from app.services.task_service import TaskService

    service = TaskService(db)
    success = service.delete_element(element_id)
    if not success:
        raise HTTPException(status_code=404, detail="元素不存在")
    return {"message": "元素已删除"}


@router.post("/pages/{page_id}/reprocess")
async def reprocess_page(
    page_id: str,
    rotation_angle: float = Body(None, embed=True),
    db: Session = Depends(get_db),
):
    page = db.query(Page).filter(Page.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="页面不存在")

    from app.analysis.preprocessor import ImagePreprocessor
    import cv2
    import os

    preprocessor = ImagePreprocessor()

    img = preprocessor.load_image(page.original_image_path)

    if rotation_angle is not None:
        processed_img = preprocessor.rotate_image(img, rotation_angle)
    else:
        processed_img, angle = preprocessor.preprocess(img)
        rotation_angle = angle

    processed_img = preprocessor.denoise(processed_img)

    result_dir = os.path.dirname(page.processed_image_path)
    preprocessor.save_image(processed_img, page.processed_image_path)

    page.rotation_angle = rotation_angle
    page.width = processed_img.shape[1]
    page.height = processed_img.shape[0]
    db.commit()

    return {
        "message": "页面已重新处理",
        "rotation_angle": rotation_angle,
        "width": page.width,
        "height": page.height,
    }
