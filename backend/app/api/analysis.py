from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Dict, Any

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


@router.post("/pages/{page_id}/merge-elements", response_model=List[LayoutElementResponse])
async def merge_elements(
    page_id: str,
    request: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):
    from app.services.task_service import TaskService

    element_ids = request.get("element_ids", [])
    if len(element_ids) < 2:
        raise HTTPException(status_code=400, detail="至少需要选择2个元素进行合并")

    service = TaskService(db)
    result = service.merge_elements(page_id, element_ids)
    if not result:
        raise HTTPException(status_code=400, detail="合并失败，请检查元素是否属于同一页面")
    return result


@router.post("/elements/{element_id}/split", response_model=List[LayoutElementResponse])
async def split_element(
    element_id: str,
    request: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):
    from app.services.task_service import TaskService

    split_type = request.get("split_type", "horizontal")
    split_position = request.get("split_position", 0.5)

    if split_type not in ["horizontal", "vertical"]:
        raise HTTPException(status_code=400, detail="分割类型必须是 horizontal 或 vertical")

    if split_position <= 0 or split_position >= 1:
        raise HTTPException(status_code=400, detail="分割位置必须在 0 和 1 之间")

    service = TaskService(db)
    result = service.split_element(element_id, split_type, split_position)
    if not result:
        raise HTTPException(status_code=404, detail="元素不存在或分割失败")
    return result


@router.post("/pages/{page_id}/reorder-elements", response_model=List[LayoutElementResponse])
async def reorder_elements(
    page_id: str,
    request: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):
    from app.services.task_service import TaskService

    element_order = request.get("element_order", [])
    if not element_order:
        raise HTTPException(status_code=400, detail="元素顺序列表不能为空")

    service = TaskService(db)
    result = service.reorder_elements(page_id, element_order)
    if not result:
        raise HTTPException(status_code=400, detail="重新排序失败")
    return result


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
