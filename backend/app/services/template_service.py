import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from collections import Counter

from app.models import (
    LayoutTemplate,
    TemplatePage,
    TemplateElement,
    TemplateVersion,
    TemplateCorrectionHistory,
    CompositeTemplate,
    CompositeTemplateRule,
    Task,
    Page,
    LayoutElement,
)
from app.schemas import (
    LayoutTemplateCreate,
    LayoutTemplateUpdate,
    TemplatePageCreate,
    TemplateElementCreate,
    CompositeTemplateCreate,
    CompositeTemplateUpdate,
    MatchScores,
)


class TemplateService:
    def __init__(self, db: Session):
        self.db = db

    def _compute_topology(self, elements: List[TemplateElementCreate]) -> List[TemplateElementCreate]:
        for i, elem in enumerate(elements):
            neighbors = {"above": [], "below": [], "left": [], "right": []}
            elem_center_x = elem.rel_x + elem.rel_width / 2
            elem_center_y = elem.rel_y + elem.rel_height / 2

            for j, other in enumerate(elements):
                if i == j:
                    continue
                other_center_x = other.rel_x + other.rel_width / 2
                other_center_y = other.rel_y + other.rel_height / 2

                x_overlap = (
                    max(elem.rel_x, other.rel_x)
                    < min(elem.rel_x + elem.rel_width, other.rel_x + other.rel_width)
                )
                y_overlap = (
                    max(elem.rel_y, other.rel_y)
                    < min(elem.rel_y + elem.rel_height, other.rel_y + other.rel_height)
                )

                if x_overlap and other_center_y < elem_center_y:
                    neighbors["above"].append(j)
                elif x_overlap and other_center_y > elem_center_y:
                    neighbors["below"].append(j)
                elif y_overlap and other_center_x < elem_center_x:
                    neighbors["left"].append(j)
                elif y_overlap and other_center_x > elem_center_x:
                    neighbors["right"].append(j)

            elem.topology = neighbors
        return elements

    def create_template(
        self,
        template_data: LayoutTemplateCreate,
    ) -> LayoutTemplate:
        template_id = str(uuid.uuid4())

        template = LayoutTemplate(
            id=template_id,
            name=template_data.name,
            document_types=template_data.document_types or [],
            description=template_data.description,
            match_count=0,
        )
        self.db.add(template)

        for page_data in template_data.pages:
            page_id = str(uuid.uuid4())
            page = TemplatePage(
                id=page_id,
                template_id=template_id,
                page_number=page_data.page_number,
                width=page_data.width,
                height=page_data.height,
                is_first_page=page_data.is_first_page,
            )
            self.db.add(page)

            elements_with_topology = self._compute_topology(page_data.elements)
            for elem_data in elements_with_topology:
                elem_id = str(uuid.uuid4())
                elem = TemplateElement(
                    id=elem_id,
                    template_page_id=page_id,
                    element_type=elem_data.element_type,
                    rel_x=elem_data.rel_x,
                    rel_y=elem_data.rel_y,
                    rel_width=elem_data.rel_width,
                    rel_height=elem_data.rel_height,
                    reading_order=elem_data.reading_order,
                    level=elem_data.level,
                    topology=elem_data.topology,
                )
                self.db.add(elem)

        self.db.commit()
        self.db.refresh(template)
        return template

    def create_template_from_task(
        self,
        name: str,
        document_types: List[str],
        description: Optional[str],
        task: Task,
    ) -> LayoutTemplate:
        template_id = str(uuid.uuid4())

        template = LayoutTemplate(
            id=template_id,
            name=name,
            document_types=document_types or [],
            description=description,
            match_count=0,
        )
        self.db.add(template)

        sorted_pages = sorted(task.pages, key=lambda p: p.page_number)

        for page_idx, page in enumerate(sorted_pages):
            page_id = str(uuid.uuid4())
            template_page = TemplatePage(
                id=page_id,
                template_id=template_id,
                page_number=page.page_number,
                width=page.width,
                height=page.height,
                is_first_page=(page_idx == 0),
            )
            self.db.add(template_page)

            sorted_elements = sorted(page.elements, key=lambda e: e.reading_order)

            elements_data = []
            for elem in sorted_elements:
                rel_x = elem.x / page.width if page.width > 0 else 0
                rel_y = elem.y / page.height if page.height > 0 else 0
                rel_w = elem.width / page.width if page.width > 0 else 0
                rel_h = elem.height / page.height if page.height > 0 else 0

                elements_data.append(
                    TemplateElementCreate(
                        element_type=elem.element_type,
                        rel_x=rel_x,
                        rel_y=rel_y,
                        rel_width=rel_w,
                        rel_height=rel_h,
                        reading_order=elem.reading_order,
                        level=elem.level or 1,
                    )
                )

            elements_with_topology = self._compute_topology(elements_data)
            for elem_data in elements_with_topology:
                elem_id = str(uuid.uuid4())
                db_elem = TemplateElement(
                    id=elem_id,
                    template_page_id=page_id,
                    element_type=elem_data.element_type,
                    rel_x=elem_data.rel_x,
                    rel_y=elem_data.rel_y,
                    rel_width=elem_data.rel_width,
                    rel_height=elem_data.rel_height,
                    reading_order=elem_data.reading_order,
                    level=elem_data.level,
                    topology=elem_data.topology,
                )
                self.db.add(db_elem)

        self.db.commit()
        self.db.refresh(template)
        return template

    def check_name_exists(self, name: str, exclude_id: Optional[str] = None) -> bool:
        query = self.db.query(LayoutTemplate).filter(LayoutTemplate.name == name)
        if exclude_id:
            query = query.filter(LayoutTemplate.id != exclude_id)
        return query.first() is not None

    def _save_version_snapshot(self, template: LayoutTemplate) -> None:
        versions = sorted(template.versions, key=lambda v: v.version_number, reverse=True)
        current_max_version = versions[0].version_number if versions else 0
        next_version = current_max_version + 1

        if len(versions) >= 3:
            oldest = versions[-1]
            self.db.delete(oldest)

        snapshot = {
            "name": template.name,
            "document_types": template.document_types,
            "description": template.description,
            "pages": [
                {
                    "page_number": p.page_number,
                    "width": p.width,
                    "height": p.height,
                    "is_first_page": p.is_first_page,
                    "elements": [
                        {
                            "element_type": e.element_type,
                            "rel_x": e.rel_x,
                            "rel_y": e.rel_y,
                            "rel_width": e.rel_width,
                            "rel_height": e.rel_height,
                            "reading_order": e.reading_order,
                            "level": e.level,
                            "topology": e.topology,
                        }
                        for e in sorted(p.elements, key=lambda x: x.reading_order)
                    ],
                }
                for p in sorted(template.pages, key=lambda x: x.page_number)
            ],
        }

        version = TemplateVersion(
            id=str(uuid.uuid4()),
            template_id=template.id,
            version_number=next_version,
            snapshot=snapshot,
        )
        self.db.add(version)

    def overwrite_template(
        self,
        template_id: str,
        task: Task,
    ) -> Optional[LayoutTemplate]:
        template = self.db.query(LayoutTemplate).filter(
            LayoutTemplate.id == template_id
        ).first()
        if not template:
            return None

        self._save_version_snapshot(template)

        for page in template.pages:
            self.db.query(TemplateElement).filter(
                TemplateElement.template_page_id == page.id
            ).delete()

        self.db.query(TemplatePage).filter(
            TemplatePage.template_id == template.id
        ).delete()

        sorted_pages = sorted(task.pages, key=lambda p: p.page_number)

        for page_idx, page in enumerate(sorted_pages):
            page_id = str(uuid.uuid4())
            template_page = TemplatePage(
                id=page_id,
                template_id=template.id,
                page_number=page.page_number,
                width=page.width,
                height=page.height,
                is_first_page=(page_idx == 0),
            )
            self.db.add(template_page)

            sorted_elements = sorted(page.elements, key=lambda e: e.reading_order)

            elements_data = []
            for elem in sorted_elements:
                rel_x = elem.x / page.width if page.width > 0 else 0
                rel_y = elem.y / page.height if page.height > 0 else 0
                rel_w = elem.width / page.width if page.width > 0 else 0
                rel_h = elem.height / page.height if page.height > 0 else 0

                elements_data.append(
                    TemplateElementCreate(
                        element_type=elem.element_type,
                        rel_x=rel_x,
                        rel_y=rel_y,
                        rel_width=rel_w,
                        rel_height=rel_h,
                        reading_order=elem.reading_order,
                        level=elem.level or 1,
                    )
                )

            elements_with_topology = self._compute_topology(elements_data)
            for elem_data in elements_with_topology:
                elem_id = str(uuid.uuid4())
                db_elem = TemplateElement(
                    id=elem_id,
                    template_page_id=page_id,
                    element_type=elem_data.element_type,
                    rel_x=elem_data.rel_x,
                    rel_y=elem_data.rel_y,
                    rel_width=elem_data.rel_width,
                    rel_height=elem_data.rel_height,
                    reading_order=elem_data.reading_order,
                    level=elem_data.level,
                    topology=elem_data.topology,
                )
                self.db.add(db_elem)

        template.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(template)
        return template

    def get_template_by_name(self, name: str) -> Optional[LayoutTemplate]:
        return self.db.query(LayoutTemplate).filter(
            LayoutTemplate.name == name
        ).first()

    def list_templates(
        self,
        skip: int = 0,
        limit: int = 100,
        document_type: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
    ) -> Tuple[List[LayoutTemplate], int]:
        from sqlalchemy import cast, String

        query = self.db.query(LayoutTemplate)

        if document_type:
            query = query.filter(
                cast(LayoutTemplate.document_types, String).like(
                    f'%"{document_type}"%'
                )
            )

        if search:
            query = query.filter(LayoutTemplate.name.ilike(f"%{search}%"))

        if sort_by == "match_count":
            query = query.order_by(LayoutTemplate.match_count.desc())
        else:
            query = query.order_by(LayoutTemplate.created_at.desc())

        total = query.count()
        templates = query.offset(skip).limit(limit).all()
        return templates, total

    def get_template(self, template_id: str) -> Optional[LayoutTemplate]:
        return self.db.query(LayoutTemplate).filter(
            LayoutTemplate.id == template_id
        ).first()

    def update_template(
        self,
        template_id: str,
        update_data: LayoutTemplateUpdate,
    ) -> Optional[LayoutTemplate]:
        template = self.get_template(template_id)
        if not template:
            return None

        if update_data.name is not None:
            template.name = update_data.name
        if update_data.document_types is not None:
            template.document_types = update_data.document_types
        if update_data.description is not None:
            template.description = update_data.description

        template.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(template)
        return template

    def delete_template(self, template_id: str) -> bool:
        template = self.get_template(template_id)
        if not template:
            return False

        self.db.delete(template)
        self.db.commit()
        return True

    def list_versions(self, template_id: str) -> List[TemplateVersion]:
        return (
            self.db.query(TemplateVersion)
            .filter(TemplateVersion.template_id == template_id)
            .order_by(TemplateVersion.version_number.desc())
            .all()
        )

    def rollback_to_version(self, template_id: str, version_id: str) -> Optional[LayoutTemplate]:
        template = self.get_template(template_id)
        if not template:
            return None

        version = self.db.query(TemplateVersion).filter(
            TemplateVersion.id == version_id,
            TemplateVersion.template_id == template_id,
        ).first()
        if not version:
            return None

        self._save_version_snapshot(template)

        for page in template.pages:
            self.db.query(TemplateElement).filter(
                TemplateElement.template_page_id == page.id
            ).delete()
        self.db.query(TemplatePage).filter(
            TemplatePage.template_id == template.id
        ).delete()

        snapshot = version.snapshot

        for page_data in snapshot.get("pages", []):
            page_id = str(uuid.uuid4())
            template_page = TemplatePage(
                id=page_id,
                template_id=template.id,
                page_number=page_data.get("page_number", 1),
                width=page_data.get("width", 1000),
                height=page_data.get("height", 1414),
                is_first_page=page_data.get("is_first_page", False),
            )
            self.db.add(template_page)

            for elem_data in page_data.get("elements", []):
                elem_id = str(uuid.uuid4())
                db_elem = TemplateElement(
                    id=elem_id,
                    template_page_id=page_id,
                    element_type=elem_data.get("element_type", "paragraph"),
                    rel_x=elem_data.get("rel_x", 0),
                    rel_y=elem_data.get("rel_y", 0),
                    rel_width=elem_data.get("rel_width", 0),
                    rel_height=elem_data.get("rel_height", 0),
                    reading_order=elem_data.get("reading_order", 0),
                    level=elem_data.get("level", 1),
                    topology=elem_data.get("topology", {}),
                )
                self.db.add(db_elem)

        template.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(template)
        return template

    def increment_match_count(self, template_id: str) -> None:
        template = self.get_template(template_id)
        if template:
            template.match_count += 1
            self.db.commit()

    def _compute_element_count_similarity(
        self,
        count_a: int,
        count_b: int,
    ) -> float:
        if max(count_a, count_b) == 0:
            return 1.0
        diff = abs(count_a - count_b)
        return 1.0 - diff / max(count_a, count_b)

    def _compute_type_distribution_similarity(
        self,
        types_a: List[str],
        types_b: List[str],
    ) -> float:
        if not types_a and not types_b:
            return 1.0

        counter_a = Counter(types_a)
        counter_b = Counter(types_b)

        all_types = set(counter_a.keys()) | set(counter_b.keys())
        if not all_types:
            return 1.0

        total_a = len(types_a) or 1
        total_b = len(types_b) or 1

        diff_sum = 0.0
        for t in all_types:
            freq_a = counter_a.get(t, 0) / total_a
            freq_b = counter_b.get(t, 0) / total_b
            diff_sum += abs(freq_a - freq_b)

        return 1.0 - diff_sum / 2.0

    def _compute_grid_iou(
        self,
        template_elements: List[TemplateElement],
        target_elements: List[Dict[str, Any]],
        grid_size: int = 10,
    ) -> float:
        def build_grid(elements):
            grid = {}
            for elem in elements:
                rel_x = elem.get("rel_x") if isinstance(elem, dict) else elem.rel_x
                rel_y = elem.get("rel_y") if isinstance(elem, dict) else elem.rel_y
                rel_w = elem.get("rel_width") if isinstance(elem, dict) else elem.rel_width
                rel_h = elem.get("rel_height") if isinstance(elem, dict) else elem.rel_height

                min_col = int(rel_x * grid_size)
                max_col = int((rel_x + rel_w) * grid_size)
                min_row = int(rel_y * grid_size)
                max_row = int((rel_y + rel_h) * grid_size)

                for r in range(min_row, min(max_row + 1, grid_size)):
                    for c in range(min_col, min(max_col + 1, grid_size)):
                        grid[(r, c)] = grid.get((r, c), 0) + 1
            return grid

        grid_a = build_grid(template_elements)
        grid_b = build_grid(target_elements)

        if not grid_a and not grid_b:
            return 1.0

        all_cells = set(grid_a.keys()) | set(grid_b.keys())
        if not all_cells:
            return 1.0

        intersection = 0
        union = 0

        for cell in all_cells:
            a_val = grid_a.get(cell, 0)
            b_val = grid_b.get(cell, 0)
            intersection += min(a_val, b_val)
            union += max(a_val, b_val)

        return intersection / union if union > 0 else 0.0

    def _compute_page_similarity(
        self,
        template_page: TemplatePage,
        target_page: Page,
    ) -> float:
        template_elements = list(template_page.elements)
        target_elements = list(target_page.elements)

        target_rel_elements = []
        page_w = target_page.width or 1
        page_h = target_page.height or 1
        for elem in target_elements:
            target_rel_elements.append({
                "rel_x": elem.x / page_w,
                "rel_y": elem.y / page_h,
                "rel_width": elem.width / page_w,
                "rel_height": elem.height / page_h,
            })

        count_sim = self._compute_element_count_similarity(
            len(template_elements), len(target_elements)
        )

        template_types = [e.element_type for e in template_elements]
        target_types = [e.element_type for e in target_elements]
        type_sim = self._compute_type_distribution_similarity(
            template_types, target_types
        )

        layout_sim = self._compute_grid_iou(template_elements, target_rel_elements)

        total_sim = (
            0.2 * count_sim
            + 0.3 * type_sim
            + 0.5 * layout_sim
        )

        return total_sim

    def match_template_to_page(
        self,
        target_page: Page,
        document_types: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        query = self.db.query(LayoutTemplate)

        if document_types:
            type_filters = [
                LayoutTemplate.document_types.contains([dt])
                for dt in document_types
            ]
            from sqlalchemy import or_
            query = query.filter(or_(*type_filters))

        candidate_templates = query.all()
        if not candidate_templates:
            return None

        best_match = None
        best_similarity = 0.0
        best_page_info = None

        for template in candidate_templates:
            template_pages = sorted(template.pages, key=lambda p: p.page_number)
            if not template_pages:
                continue

            is_first = (target_page.page_number == 1)

            candidate_pages = []
            if is_first:
                first_pages = [p for p in template_pages if p.is_first_page]
                candidate_pages = first_pages or [template_pages[0]]
            else:
                candidate_pages = [p for p in template_pages if not p.is_first_page] or template_pages

            for template_page in candidate_pages:
                sim = self._compute_page_similarity(template_page, target_page)
                if sim > best_similarity:
                    best_similarity = sim
                    best_match = template
                    best_page_info = {
                        "template_page_id": template_page.id,
                        "template_page_number": template_page.page_number,
                        "page_similarity": sim,
                    }

        if best_similarity >= 0.7 and best_match:
            return {
                "template": best_match,
                "similarity": best_similarity,
                "page_info": best_page_info,
            }

        return None

    def apply_template_to_page(
        self,
        template: LayoutTemplate,
        template_page_id: str,
        target_page: Page,
    ) -> List[LayoutElement]:
        template_page = None
        for p in template.pages:
            if p.id == template_page_id:
                template_page = p
                break

        if not template_page:
            return []

        template_elements = sorted(
            template_page.elements,
            key=lambda e: (e.rel_y, e.rel_x)
        )
        target_elements = list(target_page.elements)

        page_w = target_page.width or 1
        page_h = target_page.height or 1

        matched_indices = set()

        for template_elem in template_elements:
            best_idx = -1
            best_distance = float("inf")

            t_cx = (template_elem.rel_x + template_elem.rel_width / 2)
            t_cy = (template_elem.rel_y + template_elem.rel_height / 2)

            for i, target_elem in enumerate(target_elements):
                if i in matched_indices:
                    continue

                t_rel_x = target_elem.x / page_w
                t_rel_y = target_elem.y / page_h
                t_rel_w = target_elem.width / page_w
                t_rel_h = target_elem.height / page_h
                t_cx2 = t_rel_x + t_rel_w / 2
                t_cy2 = t_rel_y + t_rel_h / 2

                distance = (t_cx - t_cx2) ** 2 + (t_cy - t_cy2) ** 2
                if distance < best_distance:
                    best_distance = distance
                    best_idx = i

            if best_idx >= 0 and best_distance < 0.02:
                target_elements[best_idx].element_type = template_elem.element_type
                target_elements[best_idx].reading_order = template_elem.reading_order
                target_elements[best_idx].level = template_elem.level
                matched_indices.add(best_idx)

        self.db.commit()
        return target_elements

    def match_and_apply_to_task(
        self,
        task: Task,
        document_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        results = []
        matched_template = None
        avg_similarity = 0.0
        match_count = 0

        original_snapshot = self._snapshot_task_elements(task)

        for page in task.pages:
            match_result = self.match_template_to_page(page, document_types)
            if match_result:
                matched_template = match_result["template"]
                avg_similarity += match_result["similarity"]
                match_count += 1

                self.apply_template_to_page(
                    match_result["template"],
                    match_result["page_info"]["template_page_id"],
                    page,
                )

                results.append({
                    "page_id": page.id,
                    "page_number": page.page_number,
                    "template_page_id": match_result["page_info"]["template_page_id"],
                    "similarity": match_result["similarity"],
                })

        if match_count > 0:
            avg_similarity /= match_count

        return {
            "matched_template_id": matched_template.id if matched_template else None,
            "matched_template_name": matched_template.name if matched_template else None,
            "avg_similarity": avg_similarity,
            "page_matches": results,
            "original_elements_snapshot": original_snapshot,
        }

    def _snapshot_task_elements(self, task: Task) -> Dict[str, Any]:
        snapshot = {}
        for page in task.pages:
            page_data = {}
            for elem in page.elements:
                page_data[elem.id] = {
                    "element_type": elem.element_type,
                    "reading_order": elem.reading_order,
                    "level": elem.level,
                }
            snapshot[page.id] = page_data
        return snapshot

    def restore_elements_from_snapshot(
        self,
        task: Task,
        snapshot: Dict[str, Any],
    ) -> None:
        for page in task.pages:
            page_snapshot = snapshot.get(page.id, {})
            for elem in page.elements:
                if elem.id in page_snapshot:
                    data = page_snapshot[elem.id]
                    elem.element_type = data.get("element_type", elem.element_type)
                    elem.reading_order = data.get("reading_order", elem.reading_order)
                    elem.level = data.get("level", elem.level)
        self.db.commit()

    def record_corrections_and_learn(
        self,
        template_id: str,
        task_id: str,
        template_snapshot: Dict[str, Any],
    ) -> List[TemplateCorrectionHistory]:
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return []

        template = self.get_template(template_id)
        if not template:
            return []

        corrections = []

        for page in task.pages:
            page_snapshot = template_snapshot.get(page.id, {})
            page_template_id = None
            page_matches = template_snapshot.get("page_matches", [])
            for pm in page_matches:
                if pm.get("page_id") == page.id:
                    page_template_id = pm.get("template_page_id")
                    break

            if not page_template_id:
                continue

            sorted_elements = sorted(page.elements, key=lambda e: e.reading_order)
            sorted_snapshot_keys = sorted(
                page_snapshot.keys(),
                key=lambda k: page_snapshot[k].get("reading_order", 0)
            )

            for idx, elem in enumerate(sorted_elements):
                if idx >= len(sorted_snapshot_keys):
                    break

                snapshot_key = sorted_snapshot_keys[idx]
                snapshot_data = page_snapshot.get(snapshot_key, {})

                original_type = snapshot_data.get("element_type")
                original_order = snapshot_data.get("reading_order", idx + 1)
                corrected_type = elem.element_type
                corrected_order = elem.reading_order

                if original_type != corrected_type or original_order != corrected_order:
                    correction = TemplateCorrectionHistory(
                        id=str(uuid.uuid4()),
                        template_id=template_id,
                        template_page_id=page_template_id,
                        task_id=task_id,
                        page_number=page.page_number,
                        element_position=idx,
                        original_type=original_type or "",
                        corrected_type=corrected_type,
                        original_reading_order=original_order,
                        corrected_reading_order=corrected_order,
                    )
                    self.db.add(correction)
                    corrections.append(correction)

        self.db.commit()

        self._auto_learn_from_corrections(template_id)

        return corrections

    def _auto_learn_from_corrections(self, template_id: str) -> None:
        corrections = self.db.query(TemplateCorrectionHistory).filter(
            TemplateCorrectionHistory.template_id == template_id
        ).all()

        pattern_counts = {}
        for corr in corrections:
            key = (
                corr.template_page_id,
                corr.element_position,
                corr.original_type,
                corr.corrected_type,
            )
            if key not in pattern_counts:
                pattern_counts[key] = 0
            pattern_counts[key] += 1

        for key, count in pattern_counts.items():
            if count >= 3:
                template_page_id, element_position, original_type, corrected_type = key

                template_page = self.db.query(TemplatePage).filter(
                    TemplatePage.id == template_page_id
                ).first()
                if not template_page:
                    continue

                sorted_elements = sorted(
                    template_page.elements,
                    key=lambda e: e.reading_order
                )
                if element_position < len(sorted_elements):
                    elem = sorted_elements[element_position]
                    if elem.element_type == original_type:
                        elem.element_type = corrected_type

        self.db.commit()

    def list_correction_histories(
        self,
        template_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[TemplateCorrectionHistory], int]:
        query = self.db.query(TemplateCorrectionHistory).filter(
            TemplateCorrectionHistory.template_id == template_id
        ).order_by(TemplateCorrectionHistory.created_at.desc())

        total = query.count()
        histories = query.offset(skip).limit(limit).all()
        return histories, total

    def _compute_page_similarity_with_scores(
        self,
        template_page: TemplatePage,
        target_page: Page,
    ) -> Tuple[float, MatchScores]:
        template_elements = list(template_page.elements)
        target_elements = list(target_page.elements)

        target_rel_elements = []
        page_w = target_page.width or 1
        page_h = target_page.height or 1
        for elem in target_elements:
            target_rel_elements.append({
                "rel_x": elem.x / page_w,
                "rel_y": elem.y / page_h,
                "rel_width": elem.width / page_w,
                "rel_height": elem.height / page_h,
            })

        count_sim = self._compute_element_count_similarity(
            len(template_elements), len(target_elements)
        )

        template_types = [e.element_type for e in template_elements]
        target_types = [e.element_type for e in target_elements]
        type_sim = self._compute_type_distribution_similarity(
            template_types, target_types
        )

        layout_sim = self._compute_grid_iou(template_elements, target_rel_elements)

        total_sim = (
            0.2 * count_sim
            + 0.3 * type_sim
            + 0.5 * layout_sim
        )

        scores = MatchScores(
            count_similarity=count_sim,
            type_similarity=type_sim,
            layout_similarity=layout_sim,
            overall=total_sim,
        )

        return total_sim, scores

    def apply_template_to_page_with_marker(
        self,
        template: LayoutTemplate,
        template_page_id: str,
        target_page: Page,
        template_name: str,
    ) -> List[LayoutElement]:
        template_page = None
        for p in template.pages:
            if p.id == template_page_id:
                template_page = p
                break

        if not template_page:
            return []

        template_elements = sorted(
            template_page.elements,
            key=lambda e: (e.rel_y, e.rel_x)
        )
        target_elements = list(target_page.elements)

        page_w = target_page.width or 1
        page_h = target_page.height or 1

        matched_indices = set()

        for template_elem in template_elements:
            best_idx = -1
            best_distance = float("inf")

            t_cx = (template_elem.rel_x + template_elem.rel_width / 2)
            t_cy = (template_elem.rel_y + template_elem.rel_height / 2)

            for i, target_elem in enumerate(target_elements):
                if i in matched_indices:
                    continue

                t_rel_x = target_elem.x / page_w
                t_rel_y = target_elem.y / page_h
                t_rel_w = target_elem.width / page_w
                t_rel_h = target_elem.height / page_h
                t_cx2 = t_rel_x + t_rel_w / 2
                t_cy2 = t_rel_y + t_rel_h / 2

                distance = (t_cx - t_cx2) ** 2 + (t_cy - t_cy2) ** 2
                if distance < best_distance:
                    best_distance = distance
                    best_idx = i

            if best_idx >= 0 and best_distance < 0.02:
                target_elements[best_idx].element_type = template_elem.element_type
                target_elements[best_idx].reading_order = template_elem.reading_order
                target_elements[best_idx].level = template_elem.level
                target_elements[best_idx].metadata = {
                    **(target_elements[best_idx].metadata or {}),
                    "from_template": True,
                    "template_name": template_name,
                    "template_id": template.id,
                    "template_page_id": template_page_id,
                    "template_element_id": template_elem.id,
                }
                matched_indices.add(best_idx)

        self.db.commit()
        return target_elements

    def match_and_apply_to_task_with_scores(
        self,
        task: Task,
        document_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        results = []
        matched_template = None
        avg_similarity = 0.0
        match_count = 0
        total_scores = None

        original_snapshot = self._snapshot_task_elements(task)

        for page in task.pages:
            match_result = self.match_template_to_page(page, document_types)
            if match_result and match_result.get("template"):
                matched_template = match_result["template"]
                template_page = next(
                    (p for p in matched_template.pages if p.id == match_result["page_info"]["template_page_id"]),
                    None
                )
                scores = None
                if template_page:
                    _, scores = self._compute_page_similarity_with_scores(template_page, page)

                if scores:
                    if total_scores is None:
                        total_scores = {
                            "count_similarity": 0,
                            "type_similarity": 0,
                            "layout_similarity": 0,
                            "overall": 0,
                        }
                    total_scores["count_similarity"] += scores.count_similarity
                    total_scores["type_similarity"] += scores.type_similarity
                    total_scores["layout_similarity"] += scores.layout_similarity
                    total_scores["overall"] += scores.overall

                avg_similarity += match_result["similarity"]
                match_count += 1

                self.apply_template_to_page_with_marker(
                    match_result["template"],
                    match_result["page_info"]["template_page_id"],
                    page,
                    match_result["template"].name,
                )

                results.append({
                    "page_id": page.id,
                    "page_number": page.page_number,
                    "template_page_id": match_result["page_info"]["template_page_id"],
                    "similarity": match_result["similarity"],
                    "scores": scores.model_dump() if scores else None,
                })

        if match_count > 0:
            avg_similarity /= match_count
            if total_scores:
                total_scores = {
                    k: v / match_count for k, v in total_scores.items()
                }

        return {
            "matched_template_id": matched_template.id if matched_template else None,
            "matched_template_name": matched_template.name if matched_template else None,
            "avg_similarity": avg_similarity,
            "scores": total_scores,
            "page_matches": results,
            "original_elements_snapshot": original_snapshot,
        }

    def create_composite_template(
        self,
        data: CompositeTemplateCreate,
    ) -> CompositeTemplate:
        composite_id = str(uuid.uuid4())

        composite = CompositeTemplate(
            id=composite_id,
            name=data.name,
            document_types=data.document_types or [],
            description=data.description,
            match_count=0,
        )
        self.db.add(composite)

        for idx, rule_data in enumerate(data.rules):
            rule = CompositeTemplateRule(
                id=str(uuid.uuid4()),
                composite_template_id=composite_id,
                base_template_id=rule_data.base_template_id,
                start_page=rule_data.start_page,
                end_page=rule_data.end_page,
                end_page_is_last=rule_data.end_page_is_last,
                order_index=idx,
            )
            self.db.add(rule)

        self.db.commit()
        self.db.refresh(composite)
        return composite

    def get_composite_template(self, template_id: str) -> Optional[CompositeTemplate]:
        return self.db.query(CompositeTemplate).filter(
            CompositeTemplate.id == template_id
        ).first()

    def list_composite_templates(
        self,
        skip: int = 0,
        limit: int = 100,
        document_type: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
    ) -> Tuple[List[CompositeTemplate], int]:
        from sqlalchemy import cast, String

        query = self.db.query(CompositeTemplate)

        if document_type:
            query = query.filter(
                cast(CompositeTemplate.document_types, String).like(
                    f'%"{document_type}"%'
                )
            )

        if search:
            query = query.filter(CompositeTemplate.name.ilike(f"%{search}%"))

        if sort_by == "match_count":
            query = query.order_by(CompositeTemplate.match_count.desc())
        else:
            query = query.order_by(CompositeTemplate.created_at.desc())

        total = query.count()
        templates = query.offset(skip).limit(limit).all()
        return templates, total

    def update_composite_template(
        self,
        template_id: str,
        update_data: CompositeTemplateUpdate,
    ) -> Optional[CompositeTemplate]:
        composite = self.get_composite_template(template_id)
        if not composite:
            return None

        if update_data.name is not None:
            composite.name = update_data.name
        if update_data.document_types is not None:
            composite.document_types = update_data.document_types
        if update_data.description is not None:
            composite.description = update_data.description

        if update_data.rules is not None:
            self.db.query(CompositeTemplateRule).filter(
                CompositeTemplateRule.composite_template_id == template_id
            ).delete()

            for idx, rule_data in enumerate(update_data.rules):
                rule = CompositeTemplateRule(
                    id=str(uuid.uuid4()),
                    composite_template_id=template_id,
                    base_template_id=rule_data.base_template_id,
                    start_page=rule_data.start_page,
                    end_page=rule_data.end_page,
                    end_page_is_last=rule_data.end_page_is_last,
                    order_index=idx,
                )
                self.db.add(rule)

        composite.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(composite)
        return composite

    def delete_composite_template(self, template_id: str) -> bool:
        composite = self.get_composite_template(template_id)
        if not composite:
            return False

        self.db.delete(composite)
        self.db.commit()
        return True

    def match_composite_template_to_task(
        self,
        task: Task,
        composite_template: CompositeTemplate,
    ) -> Dict[str, Any]:
        sorted_rules = sorted(
            composite_template.rules,
            key=lambda r: r.order_index
        )

        total_pages = task.total_pages or len(task.pages)
        results = []
        avg_similarity = 0.0
        match_count = 0
        total_scores = None
        original_snapshot = self._snapshot_task_elements(task)

        for rule in sorted_rules:
            base_template = self.get_template(rule.base_template_id)
            if not base_template:
                continue

            end_page = rule.end_page if not rule.end_page_is_last else total_pages
            if end_page is None:
                end_page = total_pages

            for page in task.pages:
                if page.page_number < rule.start_page:
                    continue
                if end_page and page.page_number > end_page:
                    continue

                match_result = self._match_specific_template_to_page(
                    page, base_template
                )
                if match_result and match_result.get("template"):
                    template_page = next(
                        (p for p in base_template.pages if p.id == match_result["page_info"]["template_page_id"]),
                        None
                    )
                    scores = None
                    if template_page:
                        _, scores = self._compute_page_similarity_with_scores(template_page, page)

                    if scores:
                        if total_scores is None:
                            total_scores = {
                                "count_similarity": 0,
                                "type_similarity": 0,
                                "layout_similarity": 0,
                                "overall": 0,
                            }
                        total_scores["count_similarity"] += scores.count_similarity
                        total_scores["type_similarity"] += scores.type_similarity
                        total_scores["layout_similarity"] += scores.layout_similarity
                        total_scores["overall"] += scores.overall

                    avg_similarity += match_result["similarity"]
                    match_count += 1

                    self.apply_template_to_page_with_marker(
                        base_template,
                        match_result["page_info"]["template_page_id"],
                        page,
                        base_template.name,
                    )

                    results.append({
                        "page_id": page.id,
                        "page_number": page.page_number,
                        "template_page_id": match_result["page_info"]["template_page_id"],
                        "base_template_id": base_template.id,
                        "base_template_name": base_template.name,
                        "similarity": match_result["similarity"],
                        "scores": scores.model_dump() if scores else None,
                    })

        if match_count > 0:
            avg_similarity /= match_count
            if total_scores:
                total_scores = {
                    k: v / match_count for k, v in total_scores.items()
                }

        return {
            "matched_template_id": composite_template.id,
            "matched_template_name": composite_template.name,
            "is_composite": True,
            "avg_similarity": avg_similarity,
            "scores": total_scores,
            "page_matches": results,
            "original_elements_snapshot": original_snapshot,
        }

    def _match_specific_template_to_page(
        self,
        target_page: Page,
        template: LayoutTemplate,
    ) -> Optional[Dict[str, Any]]:
        template_pages = sorted(template.pages, key=lambda p: p.page_number)
        if not template_pages:
            return None

        is_first = (target_page.page_number == 1)

        candidate_pages = []
        if is_first:
            first_pages = [p for p in template_pages if p.is_first_page]
            candidate_pages = first_pages or [template_pages[0]]
        else:
            candidate_pages = [p for p in template_pages if not p.is_first_page] or template_pages

        best_similarity = 0.0
        best_page_info = None

        for template_page in candidate_pages:
            sim = self._compute_page_similarity(template_page, target_page)
            if sim > best_similarity:
                best_similarity = sim
                best_page_info = {
                    "template_page_id": template_page.id,
                    "template_page_number": template_page.page_number,
                    "page_similarity": sim,
                }

        if best_similarity >= 0.7:
            return {
                "template": template,
                "similarity": best_similarity,
                "page_info": best_page_info,
            }

        return None

    def match_and_apply_to_task_composite_support(
        self,
        task: Task,
        document_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        base_result = self.match_and_apply_to_task_with_scores(task, document_types)

        from sqlalchemy import cast, String, or_
        query = self.db.query(CompositeTemplate)
        if document_types:
            type_filters = [
                CompositeTemplate.document_types.contains([dt])
                for dt in document_types
            ]
            query = query.filter(or_(*type_filters))

        composite_templates = query.all()

        best_composite_result = None
        best_composite_sim = base_result.get("avg_similarity", 0)

        for composite in composite_templates:
            result = self.match_composite_template_to_task(task, composite)
            if result["avg_similarity"] > best_composite_sim:
                best_composite_sim = result["avg_similarity"]
                best_composite_result = result

        if best_composite_result:
            composite_template = self.get_composite_template(
                best_composite_result["matched_template_id"]
            )
            if composite_template:
                composite_template.match_count += 1
                self.db.commit()
            return best_composite_result

        if base_result.get("matched_template_id"):
            base_template = self.get_template(base_result["matched_template_id"])
            if base_template:
                base_template.match_count += 1
                self.db.commit()

        return base_result

    def increment_composite_match_count(self, template_id: str) -> None:
        template = self.get_composite_template(template_id)
        if template:
            template.match_count += 1
            self.db.commit()
