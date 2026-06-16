import os
import uuid
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models import Task, Page, LayoutElement, Table
from app.config import settings
from app.analysis.preprocessor import ImagePreprocessor
from app.analysis.layout_detector import LayoutDetector
from app.analysis.table_analyzer import TableStructureAnalyzer
from app.analysis.output_generator import OutputGenerator
import pytesseract


class TaskService:
    def __init__(self, db: Session):
        self.db = db
        self.preprocessor = ImagePreprocessor()
        self.layout_detector = LayoutDetector()
        self.table_analyzer = TableStructureAnalyzer()
        self.output_generator = OutputGenerator()

    def create_task(self, filename: str) -> Task:
        task_id = str(uuid.uuid4())
        expires_at = datetime.now() + timedelta(days=settings.result_retention_days)

        task = Task(
            id=task_id,
            filename=filename,
            status="pending",
            total_pages=0,
            current_page=0,
            expires_at=expires_at,
        )

        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)

        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        return self.db.query(Task).filter(Task.id == task_id).first()

    def list_tasks(self, skip: int = 0, limit: int = 100) -> List[Task]:
        return (
            self.db.query(Task)
            .order_by(Task.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update_task_status(
        self,
        task_id: str,
        status: str,
        error_message: str = None
    ) -> Optional[Task]:
        task = self.get_task(task_id)
        if not task:
            return None

        task.status = status
        if error_message:
            task.error_message = error_message

        self.db.commit()
        self.db.refresh(task)
        return task

    def update_task_progress(
        self,
        task_id: str,
        current_page: int,
        total_pages: int = None
    ) -> Optional[Task]:
        task = self.get_task(task_id)
        if not task:
            return None

        task.current_page = current_page
        if total_pages:
            task.total_pages = total_pages

        self.db.commit()
        self.db.refresh(task)
        return task

    def get_task_upload_dir(self, task_id: str) -> str:
        return os.path.join(settings.upload_dir, task_id)

    def get_task_result_dir(self, task_id: str) -> str:
        return os.path.join(settings.result_dir, task_id)

    def process_file(self, task_id: str, file_path: str) -> None:
        task = self.get_task(task_id)
        if not task:
            return

        try:
            self.update_task_status(task_id, "processing")

            upload_dir = self.get_task_upload_dir(task_id)
            result_dir = self.get_task_result_dir(task_id)
            os.makedirs(upload_dir, exist_ok=True)
            os.makedirs(result_dir, exist_ok=True)

            image_paths = []

            if file_path.lower().endswith(".pdf"):
                image_paths = self.preprocessor.process_pdf(file_path)
            else:
                ext = os.path.splitext(file_path)[1].lower()
                if ext in [".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp"]:
                    image_paths = [file_path]
                else:
                    raise ValueError(f"不支持的文件格式: {ext}")

            total_pages = len(image_paths)
            task.total_pages = total_pages
            task.status = "processing"
            self.db.commit()

            for page_idx, image_path in enumerate(image_paths):
                try:
                    self._process_page(task_id, page_idx + 1, image_path, result_dir)
                    task.current_page = page_idx + 1
                    self.db.commit()
                except Exception as e:
                    print(f"Error processing page {page_idx + 1}: {e}")
                    page_id = str(uuid.uuid4())
                    width, height = self.preprocessor.get_image_size(image_path)
                    page = Page(
                        id=page_id,
                        task_id=task_id,
                        page_number=page_idx + 1,
                        width=width,
                        height=height,
                        original_image_path=image_path,
                        processed_image_path=image_path,
                        status="failed",
                        error_message=str(e),
                    )
                    self.db.add(page)
                    self.db.commit()

            task.status = "completed"
            task.updated_at = datetime.now()
            self.db.commit()

        except Exception as e:
            task.status = "failed"
            task.error_message = str(e)
            self.db.commit()

    def _process_page(
        self,
        task_id: str,
        page_number: int,
        image_path: str,
        result_dir: str
    ) -> None:
        page_id = str(uuid.uuid4())

        img = self.preprocessor.load_image(image_path)
        processed_img, angle = self.preprocessor.preprocess(img)

        page_result_dir = os.path.join(result_dir, f"page_{page_number:04d}")
        os.makedirs(page_result_dir, exist_ok=True)

        original_path = os.path.join(page_result_dir, "original.png")
        processed_path = os.path.join(page_result_dir, "processed.png")

        self.preprocessor.save_image(img, original_path)
        self.preprocessor.save_image(processed_img, processed_path)

        width, height = processed_img.shape[1], processed_img.shape[0]

        page = Page(
            id=page_id,
            task_id=task_id,
            page_number=page_number,
            width=width,
            height=height,
            original_image_path=original_path,
            processed_image_path=processed_path,
            rotation_angle=angle,
            status="completed",
        )
        self.db.add(page)
        self.db.flush()

        elements = self.layout_detector.detect_layout_elements(processed_img)

        columns_count = self.layout_detector.detect_columns(processed_img)
        elements = self.layout_detector.compute_reading_order(elements, columns_count)

        table_bboxes = []
        table_element_map = {}
        for elem in elements:
            if elem.element_type == "table":
                bbox = (int(elem.x), int(elem.y), int(elem.width), int(elem.height))
                table_bboxes.append(bbox)
                table_element_map[bbox] = elem.id

        table_structures = self.table_analyzer.analyze_tables(
            processed_img, table_bboxes, perform_ocr=False
        )

        for bbox, table_struct in zip(table_bboxes, table_structures):
            element_id = table_element_map.get(bbox)
            table = Table(
                id=str(uuid.uuid4()),
                page_id=page_id,
                element_id=element_id,
                rows=table_struct.rows,
                cols=table_struct.cols,
                has_header=table_struct.has_header,
                cells=[c.to_dict() for c in table_struct.cells],
            )
            self.db.add(table)

        gray_img = self.preprocessor.to_grayscale(processed_img)

        for elem in elements:
            if elem.element_type in ["paragraph", "title", "header", "footer", "caption", "list"]:
                x, y, w, h = int(elem.x), int(elem.y), int(elem.width), int(elem.height)
                x = max(0, x)
                y = max(0, y)
                w = min(w, width - x)
                h = min(h, height - y)

                if w > 0 and h > 0:
                    roi = gray_img[y:y + h, x:x + w]
                    try:
                        text = pytesseract.image_to_string(roi, lang="chi_sim+eng")
                        elem.text_content = text.strip()
                    except Exception:
                        elem.text_content = ""

            db_elem = LayoutElement(
                id=elem.id,
                page_id=page_id,
                element_type=elem.element_type,
                x=elem.x,
                y=elem.y,
                width=elem.width,
                height=elem.height,
                confidence=elem.confidence,
                reading_order=elem.reading_order,
                level=elem.level,
                text_content=elem.text_content,
                metadata=elem.metadata,
            )
            self.db.add(db_elem)

        self.db.commit()

    def retry_task(self, task_id: str) -> Optional[Task]:
        task = self.get_task(task_id)
        if not task:
            return None

        if task.status not in ["failed", "completed"]:
            return None

        for page in task.pages:
            self.db.query(LayoutElement).filter(
                LayoutElement.page_id == page.id
            ).delete()
            self.db.query(Table).filter(
                Table.page_id == page.id
            ).delete()

        self.db.query(Page).filter(Page.task_id == task_id).delete()

        task.status = "pending"
        task.current_page = 0
        task.error_message = None
        task.updated_at = datetime.now()

        self.db.commit()
        self.db.refresh(task)
        return task

    def get_page(self, page_id: str) -> Optional[Page]:
        return self.db.query(Page).filter(Page.id == page_id).first()

    def update_element(
        self,
        element_id: str,
        element_data: dict
    ) -> Optional[LayoutElement]:
        element = self.db.query(LayoutElement).filter(
            LayoutElement.id == element_id
        ).first()
        if not element:
            return None

        for key, value in element_data.items():
            if hasattr(element, key):
                setattr(element, key, value)

        self.db.commit()
        self.db.refresh(element)
        return element

    def delete_element(self, element_id: str) -> bool:
        element = self.db.query(LayoutElement).filter(
            LayoutElement.id == element_id
        ).first()
        if not element:
            return False

        self.db.delete(element)
        self.db.commit()
        return True

    def generate_output(self, task_id: str, output_format: str) -> str:
        task = self.get_task(task_id)
        if not task:
            raise ValueError("任务不存在")

        pages_data = []
        for page in task.pages:
            elements = [
                {
                    "id": e.id,
                    "element_type": e.element_type,
                    "x": e.x,
                    "y": e.y,
                    "width": e.width,
                    "height": e.height,
                    "confidence": e.confidence,
                    "reading_order": e.reading_order,
                    "level": e.level,
                    "text_content": e.text_content or "",
                    "metadata": e.metadata or {},
                    "image_path": e.image_path or "",
                }
                for e in page.elements
            ]

            tables = [
                {
                    "id": t.id,
                    "element_id": t.element_id,
                    "rows": t.rows,
                    "cols": t.cols,
                    "has_header": t.has_header,
                    "cells": t.cells or [],
                }
                for t in page.tables
            ]

            pages_data.append({
                "page_number": page.page_number,
                "width": page.width,
                "height": page.height,
                "rotation_angle": page.rotation_angle,
                "elements": elements,
                "tables": tables,
                "columns_count": 1,
            })

        result_dir = self.get_task_result_dir(task_id)
        os.makedirs(result_dir, exist_ok=True)

        if output_format == "json":
            content = self.output_generator.generate_json(task_id, pages_data)
        elif output_format == "html":
            content = self.output_generator.generate_html(task_id, pages_data)
        elif output_format == "markdown":
            content = self.output_generator.generate_markdown(task_id, pages_data)
        else:
            raise ValueError(f"不支持的输出格式: {output_format}")

        output_path = self.output_generator.save_output(
            content, result_dir, "output", output_format
        )

        return output_path

    def cleanup_expired_tasks(self) -> int:
        now = datetime.now()
        expired_tasks = self.db.query(Task).filter(Task.expires_at < now).all()

        count = 0
        for task in expired_tasks:
            task_dir = self.get_task_upload_dir(task.id)
            result_dir = self.get_task_result_dir(task.id)

            import shutil
            if os.path.exists(task_dir):
                shutil.rmtree(task_dir, ignore_errors=True)
            if os.path.exists(result_dir):
                shutil.rmtree(result_dir, ignore_errors=True)

            self.db.delete(task)
            count += 1

        self.db.commit()
        return count
