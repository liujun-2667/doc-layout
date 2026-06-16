import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import uuid


@dataclass
class LayoutElement:
    id: str
    element_type: str
    x: float
    y: float
    width: float
    height: float
    confidence: float
    reading_order: int = 0
    level: int = 1
    text_content: Optional[str] = None
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "element_type": self.element_type,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "confidence": self.confidence,
            "reading_order": self.reading_order,
            "level": self.level,
            "text_content": self.text_content,
            "metadata": self.metadata,
        }


class LayoutDetector:
    def __init__(self):
        self.element_colors = {
            "title": (0, 0, 255),
            "paragraph": (255, 0, 0),
            "table": (0, 255, 0),
            "figure": (0, 165, 255),
            "caption": (128, 0, 128),
            "header": (255, 0, 255),
            "footer": (255, 255, 0),
            "page_number": (0, 255, 255),
            "list": (128, 128, 0),
            "formula": (0, 128, 128),
            "stamp": (128, 0, 0),
        }

    @staticmethod
    def connected_components_analysis(binary_img: np.ndarray) -> List[Tuple[int, int, int, int]]:
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            ~binary_img if binary_img[0, 0] == 255 else binary_img,
            connectivity=8
        )
        
        regions = []
        min_area = 100
        
        for i in range(1, num_labels):
            x = stats[i, cv2.CC_STAT_LEFT]
            y = stats[i, cv2.CC_STAT_TOP]
            w = stats[i, cv2.CC_STAT_WIDTH]
            h = stats[i, cv2.CC_STAT_HEIGHT]
            area = stats[i, cv2.CC_STAT_AREA]
            
            if area >= min_area:
                regions.append((x, y, w, h))
        
        return regions

    @staticmethod
    def projection_profile_analysis(
        img: np.ndarray,
        axis: int = 0
    ) -> np.ndarray:
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img
        
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
        
        if axis == 0:
            profile = np.sum(binary, axis=1)
        else:
            profile = np.sum(binary, axis=0)
        
        return profile

    @staticmethod
    def detect_table_lines(img: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img
        
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
        
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        horizontal_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel)
        horizontal_lines = cv2.dilate(horizontal_lines, horizontal_kernel, iterations=1)
        
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
        vertical_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel)
        vertical_lines = cv2.dilate(vertical_lines, vertical_kernel, iterations=1)
        
        return horizontal_lines, vertical_lines

    def detect_tables(self, img: np.ndarray) -> List[Tuple[int, int, int, int]]:
        horizontal_lines, vertical_lines = self.detect_table_lines(img)
        
        table_mask = cv2.add(horizontal_lines, vertical_lines)
        
        contours, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        tables = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w > 100 and h > 50:
                tables.append((x, y, w, h))
        
        return tables

    def detect_text_blocks(self, img: np.ndarray) -> List[Tuple[int, int, int, int, str]]:
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img
        
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 5))
        dilated = cv2.dilate(binary, kernel, iterations=2)
        
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        text_blocks = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w > 20 and h > 10:
                aspect_ratio = w / h if h > 0 else 0
                if aspect_ratio < 30:
                    block_type = "paragraph"
                    text_blocks.append((x, y, w, h, block_type))
        
        return text_blocks

    def detect_headers_footers(
        self,
        img: np.ndarray,
        text_blocks: List[Tuple[int, int, int, int, str]]
    ) -> List[Tuple[int, int, int, int, str]]:
        height = img.shape[0]
        header_zone = height * 0.1
        footer_zone = height * 0.9
        
        updated_blocks = []
        for (x, y, w, h, block_type) in text_blocks:
            center_y = y + h / 2
            
            if center_y < header_zone and h < height * 0.05:
                block_type = "header"
            elif center_y > footer_zone and h < height * 0.05:
                if w < 100:
                    block_type = "page_number"
                else:
                    block_type = "footer"
            
            updated_blocks.append((x, y, w, h, block_type))
        
        return updated_blocks

    def detect_titles(
        self,
        img: np.ndarray,
        text_blocks: List[Tuple[int, int, int, int, str]]
    ) -> List[Tuple[int, int, int, int, str, int]]:
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img
        
        heights = []
        for (x, y, w, h, block_type) in text_blocks:
            if block_type == "paragraph":
                heights.append(h)
        
        if not heights:
            return [(x, y, w, h, t, 1) for (x, y, w, h, t) in text_blocks]
        
        median_height = np.median(heights)
        
        result = []
        for (x, y, w, h, block_type) in text_blocks:
            level = 1
            if block_type == "paragraph" and h > median_height * 1.3:
                block_type = "title"
                if h > median_height * 2:
                    level = 1
                elif h > median_height * 1.6:
                    level = 2
                else:
                    level = 3
            result.append((x, y, w, h, block_type, level))
        
        return result

    def merge_overlapping_regions(
        self,
        regions: List[Tuple[int, int, int, int, str]]
    ) -> List[Tuple[int, int, int, int, str]]:
        if not regions:
            return []
        
        sorted_regions = sorted(regions, key=lambda r: (r[1], r[0]))
        
        merged = []
        current = sorted_regions[0]
        
        for i in range(1, len(sorted_regions)):
            next_reg = sorted_regions[i]
            
            cy, ch = current[1], current[3]
            ny, nh = next_reg[1], next_reg[3]
            
            vertical_gap = ny - (cy + ch)
            horizontal_overlap = min(
                current[0] + current[2], next_reg[0] + next_reg[2]
            ) - max(current[0], next_reg[0])
            
            if vertical_gap < 20 and horizontal_overlap > 20 and current[4] == next_reg[4]:
                new_x = min(current[0], next_reg[0])
                new_y = min(current[1], next_reg[1])
                new_w = max(current[0] + current[2], next_reg[0] + next_reg[2]) - new_x
                new_h = max(current[1] + current[3], next_reg[1] + next_reg[3]) - new_y
                current = (new_x, new_y, new_w, new_h, current[4])
            else:
                merged.append(current)
                current = next_reg
        
        merged.append(current)
        return merged

    def detect_layout_elements(self, img: np.ndarray) -> List[LayoutElement]:
        elements = []
        
        tables = self.detect_tables(img)
        for (x, y, w, h) in tables:
            elements.append(LayoutElement(
                id=str(uuid.uuid4()),
                element_type="table",
                x=float(x),
                y=float(y),
                width=float(w),
                height=float(h),
                confidence=0.85,
            ))
        
        text_blocks = self.detect_text_blocks(img)
        text_blocks = self.detect_headers_footers(img, text_blocks)
        text_blocks_with_levels = self.detect_titles(img, text_blocks)
        
        for (x, y, w, h, block_type, level) in text_blocks_with_levels:
            is_inside_table = False
            for (tx, ty, tw, th) in tables:
                if x >= tx - 5 and y >= ty - 5 and x + w <= tx + tw + 5 and y + h <= ty + th + 5:
                    is_inside_table = True
                    break
            
            if not is_inside_table:
                element = LayoutElement(
                    id=str(uuid.uuid4()),
                    element_type=block_type,
                    x=float(x),
                    y=float(y),
                    width=float(w),
                    height=float(h),
                    confidence=0.75,
                    level=level,
                )
                
                if block_type == "title":
                    element.metadata["heading_level"] = level
                
                elements.append(element)
        
        return elements

    def compute_reading_order(self, elements: List[LayoutElement], columns_count: int = 1) -> List[LayoutElement]:
        if not elements:
            return elements

        if columns_count == 1:
            sorted_elements = sorted(elements, key=lambda e: (e.y, e.x))
        else:
            width = max(e.x + e.width for e in elements)
            column_width = width / columns_count

            column_elements = [[] for _ in range(columns_count)]
            span_elements = []

            for element in elements:
                element_center = element.x + element.width / 2
                col = int(element_center / column_width)
                col = min(col, columns_count - 1)

                if element.width > column_width * 1.2:
                    span_elements.append(element)
                else:
                    column_elements[col].append(element)

            for i in range(columns_count):
                column_elements[i].sort(key=lambda e: e.y)

            sorted_elements = []

            for span_elem in sorted(span_elements, key=lambda e: e.y):
                sorted_elements.append(span_elem)

            for col_idx in range(columns_count):
                for elem in column_elements[col_idx]:
                    insert_at = len(sorted_elements)
                    for i, existing in enumerate(sorted_elements):
                        if elem.y < existing.y:
                            insert_at = i
                            break
                    sorted_elements.insert(insert_at, elem)

            final_sorted = []
            remaining_span = list(sorted(span_elements, key=lambda e: e.y))
            span_idx = 0

            for col_idx in range(columns_count):
                for elem in column_elements[col_idx]:
                    while span_idx < len(remaining_span) and remaining_span[span_idx].y <= elem.y:
                        final_sorted.append(remaining_span[span_idx])
                        span_idx += 1
                    final_sorted.append(elem)

            while span_idx < len(remaining_span):
                final_sorted.append(remaining_span[span_idx])
                span_idx += 1

            sorted_elements = final_sorted

        for i, element in enumerate(sorted_elements):
            element.reading_order = i + 1

        return sorted_elements

    def detect_columns(self, img: np.ndarray) -> int:
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img
        
        h, w = gray.shape
        
        middle_section = gray[int(h * 0.2):int(h * 0.8), :]
        
        _, binary = cv2.threshold(middle_section, 127, 255, cv2.THRESH_BINARY_INV)
        
        horizontal_proj = np.sum(binary, axis=0)
        
        white_space_threshold = np.max(horizontal_proj) * 0.05
        gap_regions = []
        in_gap = False
        gap_start = 0
        
        for i in range(len(horizontal_proj)):
            if horizontal_proj[i] < white_space_threshold:
                if not in_gap:
                    gap_start = i
                    in_gap = True
            else:
                if in_gap:
                    gap_width = i - gap_start
                    if gap_width > w * 0.02:
                        gap_regions.append((gap_start, i, gap_width))
                    in_gap = False
        
        significant_gaps = [g for g in gap_regions if g[2] > w * 0.05]
        
        if len(significant_gaps) >= 2:
            return 3
        elif len(significant_gaps) == 1:
            return 2
        else:
            return 1
