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
