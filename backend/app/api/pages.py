from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import Page
from app.schemas import PageResponse, LayoutElementResponse

router = APIRouter()


@router.get("/{page_id}", response_model=PageResponse)
async def get_page(
    page_id: str,
    db: Session = Depends(get_db),
):
    page = db.query(Page).filter(Page.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="页面不存在")
    return page


@router.get("/{page_id}/elements", response_model=List[LayoutElementResponse])
async def get_page_elements(
    page_id: str,
    db: Session = Depends(get_db),
):
    page = db.query(Page).filter(Page.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="页面不存在")
    return page.elements
