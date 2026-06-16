from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class BBox(BaseModel):
    x: float
    y: float
    width: float
    height: float


class LayoutElementBase(BaseModel):
    element_type: str
    x: float
    y: float
    width: float
    height: float
    confidence: float
    reading_order: int
    level: int = 1
    text_content: Optional[str] = None
    metadata: Dict[str, Any] = {}


class LayoutElementCreate(LayoutElementBase):
    pass


class LayoutElementResponse(LayoutElementBase):
    id: str
    page_id: str

    class Config:
        from_attributes = True


class TableCell(BaseModel):
    row: int
    col: int
    rowspan: int = 1
    colspan: int = 1
    content: str = ""
    is_header: bool = False


class TableBase(BaseModel):
    rows: int
    cols: int
    has_header: bool = False
    cells: List[TableCell] = []


class TableCreate(TableBase):
    element_id: Optional[str] = None


class TableResponse(TableBase):
    id: str
    page_id: str

    class Config:
        from_attributes = True


class PageBase(BaseModel):
    page_number: int
    width: int
    height: int
    original_image_path: str
    processed_image_path: str
    rotation_angle: float = 0.0
    status: str = "pending"


class PageCreate(PageBase):
    pass


class PageResponse(PageBase):
    id: str
    task_id: str
    elements: List[LayoutElementResponse] = []
    tables: List[TableResponse] = []

    class Config:
        from_attributes = True


class TaskBase(BaseModel):
    filename: str
    status: str = "pending"
    total_pages: int = 0
    current_page: int = 0


class TaskCreate(TaskBase):
    pass


class TaskResponse(TaskBase):
    id: str
    error_message: Optional[str] = None
    template_match_info: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    pages: List[PageResponse] = []

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    tasks: List[TaskResponse]
    total: int


class LayoutAnalysisResult(BaseModel):
    elements: List[LayoutElementResponse]
    tables: List[TableResponse]
    reading_order: List[int]
    columns_count: int = 1


class OutputFormatRequest(BaseModel):
    format: str = "json"


class TemplateElementBase(BaseModel):
    element_type: str
    rel_x: float
    rel_y: float
    rel_width: float
    rel_height: float
    reading_order: int
    level: int = 1
    topology: Dict[str, Any] = {}


class TemplateElementCreate(TemplateElementBase):
    pass


class TemplateElementResponse(TemplateElementBase):
    id: str
    template_page_id: str

    class Config:
        from_attributes = True


class TemplatePageBase(BaseModel):
    page_number: int
    width: int = 1000
    height: int = 1414
    is_first_page: bool = False


class TemplatePageCreate(TemplatePageBase):
    elements: List[TemplateElementCreate] = []


class TemplatePageResponse(TemplatePageBase):
    id: str
    template_id: str
    elements: List[TemplateElementResponse] = []

    class Config:
        from_attributes = True


class LayoutTemplateBase(BaseModel):
    name: str
    document_types: List[str] = []
    description: Optional[str] = None


class LayoutTemplateCreate(LayoutTemplateBase):
    pages: List[TemplatePageCreate] = []
    source_task_id: Optional[str] = None


class LayoutTemplateUpdate(BaseModel):
    name: Optional[str] = None
    document_types: Optional[List[str]] = None
    description: Optional[str] = None


class LayoutTemplateResponse(LayoutTemplateBase):
    id: str
    match_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime]
    pages: List[TemplatePageResponse] = []

    class Config:
        from_attributes = True


class TemplateVersionBase(BaseModel):
    version_number: int
    snapshot: Dict[str, Any] = {}


class TemplateVersionResponse(TemplateVersionBase):
    id: str
    template_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class TemplateListResponse(BaseModel):
    templates: List[LayoutTemplateResponse]
    total: int


class MatchResult(BaseModel):
    template: LayoutTemplateResponse
    similarity: float
    page_matches: List[Dict[str, Any]] = []


class ApplyTemplateRequest(BaseModel):
    template_id: str
    accept: bool = True


class SaveTemplateConflictRequest(BaseModel):
    action: str
    new_name: Optional[str] = None
