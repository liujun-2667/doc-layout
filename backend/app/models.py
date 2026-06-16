from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, index=True)
    filename = Column(String, index=True)
    status = Column(String, default="pending", index=True)
    total_pages = Column(Integer, default=0)
    current_page = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    template_match_info = Column(JSON, default=dict, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)

    pages = relationship("Page", back_populates="task", cascade="all, delete-orphan")


class Page(Base):
    __tablename__ = "pages"

    id = Column(String, primary_key=True, index=True)
    task_id = Column(String, ForeignKey("tasks.id"), index=True)
    page_number = Column(Integer)
    width = Column(Integer)
    height = Column(Integer)
    original_image_path = Column(String)
    processed_image_path = Column(String)
    rotation_angle = Column(Float, default=0.0)
    status = Column(String, default="pending")
    error_message = Column(Text, nullable=True)

    task = relationship("Task", back_populates="pages")
    elements = relationship("LayoutElement", back_populates="page", cascade="all, delete-orphan")
    tables = relationship("Table", back_populates="page", cascade="all, delete-orphan")


class LayoutElement(Base):
    __tablename__ = "layout_elements"

    id = Column(String, primary_key=True, index=True)
    page_id = Column(String, ForeignKey("pages.id"), index=True)
    element_type = Column(String, index=True)
    x = Column(Float)
    y = Column(Float)
    width = Column(Float)
    height = Column(Float)
    confidence = Column(Float)
    reading_order = Column(Integer)
    level = Column(Integer, default=1)
    text_content = Column(Text, nullable=True)
    image_path = Column(String, nullable=True)
    metadata = Column(JSON, default=dict)

    page = relationship("Page", back_populates="elements")


class Table(Base):
    __tablename__ = "tables"

    id = Column(String, primary_key=True, index=True)
    page_id = Column(String, ForeignKey("pages.id"), index=True)
    element_id = Column(String, nullable=True)
    rows = Column(Integer)
    cols = Column(Integer)
    has_header = Column(Boolean, default=False)
    cells = Column(JSON, default=list)

    page = relationship("Page", back_populates="tables")


class LayoutTemplate(Base):
    __tablename__ = "layout_templates"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    document_types = Column(JSON, default=list)
    description = Column(Text, nullable=True)
    match_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    pages = relationship("TemplatePage", back_populates="template", cascade="all, delete-orphan")
    versions = relationship("TemplateVersion", back_populates="template", cascade="all, delete-orphan")


class TemplatePage(Base):
    __tablename__ = "template_pages"

    id = Column(String, primary_key=True, index=True)
    template_id = Column(String, ForeignKey("layout_templates.id"), index=True)
    page_number = Column(Integer, default=1)
    width = Column(Integer, default=1000)
    height = Column(Integer, default=1414)
    is_first_page = Column(Boolean, default=False)

    template = relationship("LayoutTemplate", back_populates="pages")
    elements = relationship("TemplateElement", back_populates="page", cascade="all, delete-orphan")


class TemplateElement(Base):
    __tablename__ = "template_elements"

    id = Column(String, primary_key=True, index=True)
    template_page_id = Column(String, ForeignKey("template_pages.id"), index=True)
    element_type = Column(String, index=True)
    rel_x = Column(Float)
    rel_y = Column(Float)
    rel_width = Column(Float)
    rel_height = Column(Float)
    reading_order = Column(Integer)
    level = Column(Integer, default=1)
    topology = Column(JSON, default=dict)

    page = relationship("TemplatePage", back_populates="elements")


class TemplateVersion(Base):
    __tablename__ = "template_versions"

    id = Column(String, primary_key=True, index=True)
    template_id = Column(String, ForeignKey("layout_templates.id"), index=True)
    version_number = Column(Integer)
    snapshot = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    template = relationship("LayoutTemplate", back_populates="versions")


class TemplateCorrectionHistory(Base):
    __tablename__ = "template_correction_histories"

    id = Column(String, primary_key=True, index=True)
    template_id = Column(String, ForeignKey("layout_templates.id"), index=True)
    template_page_id = Column(String, ForeignKey("template_pages.id"), index=True)
    task_id = Column(String, index=True)
    page_number = Column(Integer)
    element_position = Column(Integer)
    original_type = Column(String)
    corrected_type = Column(String)
    original_reading_order = Column(Integer)
    corrected_reading_order = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    template = relationship("LayoutTemplate")


class CompositeTemplate(Base):
    __tablename__ = "composite_templates"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    document_types = Column(JSON, default=list)
    description = Column(Text, nullable=True)
    match_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    rules = relationship("CompositeTemplateRule", back_populates="composite_template", cascade="all, delete-orphan")


class CompositeTemplateRule(Base):
    __tablename__ = "composite_template_rules"

    id = Column(String, primary_key=True, index=True)
    composite_template_id = Column(String, ForeignKey("composite_templates.id"), index=True)
    base_template_id = Column(String, ForeignKey("layout_templates.id"), index=True)
    start_page = Column(Integer)
    end_page = Column(Integer, nullable=True)
    end_page_is_last = Column(Boolean, default=False)
    order_index = Column(Integer)

    composite_template = relationship("CompositeTemplate", back_populates="rules")
    base_template = relationship("LayoutTemplate")
