import cv2
import numpy as np
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass, field
import pytesseract


@dataclass
class TableCell:
    row: int
    col: int
    rowspan: int = 1
    colspan: int = 1
    content: str = ""
    is_header: bool = False
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0

    def to_dict(self) -> dict:
        return {
            "row": self.row,
            "col": self.col,
            "rowspan": self.rowspan,
            "colspan": self.colspan,
            "content": self.content,
            "is_header": self.is_header,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }


@dataclass
class TableStructure:
    rows: int = 0
    cols: int = 0
    has_header: bool = False
    cells: List[TableCell] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "rows": self.rows,
            "cols": self.cols,
            "has_header": self.has_header,
            "cells": [c.to_dict() for c in self.cells],
        }


class TableStructureAnalyzer:
    def __init__(self):
        pass

    def extract_table_image(
        self,
        full_img: np.ndarray,
        table_bbox: Tuple[int, int, int, int]
    ) -> np.ndarray:
        x, y, w, h = table_bbox
        padding = 5
        x = max(0, x - padding)
        y = max(0, y - padding)
        w = min(full_img.shape[1] - x, w + 2 * padding)
        h = min(full_img.shape[0] - y, h + 2 * padding)
        return full_img[y:y + h, x:x + w].copy()

    def detect_table_lines(
        self,
        table_img: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        if len(table_img.shape) == 3:
            gray = cv2.cvtColor(table_img, cv2.COLOR_BGR2GRAY)
        else:
            gray = table_img
        
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
        
        h, w = binary.shape
        
        horizontal_kernel_length = max(20, w // 10)
        horizontal_kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT, (horizontal_kernel_length, 1)
        )
        horizontal_lines = cv2.morphologyEx(
            binary, cv2.MORPH_OPEN, horizontal_kernel
        )
        horizontal_lines = cv2.dilate(
            horizontal_lines, np.ones((2, 1), np.uint8), iterations=1
        )
        
        vertical_kernel_length = max(20, h // 10)
        vertical_kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT, (1, vertical_kernel_length)
        )
        vertical_lines = cv2.morphologyEx(
            binary, cv2.MORPH_OPEN, vertical_kernel
        )
        vertical_lines = cv2.dilate(
            vertical_lines, np.ones((1, 2), np.uint8), iterations=1
        )
        
        return horizontal_lines, vertical_lines

    def get_line_positions(
        self,
        line_img: np.ndarray,
        axis: int = 0
    ) -> List[int]:
        if axis == 0:
            projection = np.sum(line_img, axis=1)
        else:
            projection = np.sum(line_img, axis=0)
        
        threshold = np.max(projection) * 0.1
        line_positions = []
        
        in_line = False
        line_start = 0
        
        for i in range(len(projection)):
            if projection[i] > threshold:
                if not in_line:
                    line_start = i
                    in_line = True
            else:
                if in_line:
                    line_positions.append((line_start + i) // 2)
                    in_line = False
        
        if in_line:
            line_positions.append((line_start + len(projection) - 1) // 2)
        
        return line_positions

    def detect_cell_boundaries(
        self,
        table_img: np.ndarray,
        horizontal_lines: np.ndarray,
        vertical_lines: np.ndarray
    ) -> Tuple[List[int], List[int]]:
        h_positions = self.get_line_positions(horizontal_lines, axis=0)
        v_positions = self.get_line_positions(vertical_lines, axis=1)
        
        h, w = table_img.shape[:2]
        
        if len(h_positions) < 2:
            h_positions = [0, h]
        else:
            if h_positions[0] > 10:
                h_positions = [0] + h_positions
            if h - h_positions[-1] > 10:
                h_positions = h_positions + [h]
        
        if len(v_positions) < 2:
            v_positions = [0, w]
        else:
            if v_positions[0] > 10:
                v_positions = [0] + v_positions
            if w - v_positions[-1] > 10:
                v_positions = v_positions + [w]
        
        return h_positions, v_positions

    def infer_borderless_table(
        self,
        table_img: np.ndarray
    ) -> Tuple[List[int], List[int]]:
        if len(table_img.shape) == 3:
            gray = cv2.cvtColor(table_img, cv2.COLOR_BGR2GRAY)
        else:
            gray = table_img
        
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
        
        h, w = binary.shape
        
        row_proj = np.sum(binary, axis=1)
        row_gaps = []
        in_gap = False
        gap_start = 0
        
        for i in range(h):
            if row_proj[i] < 10:
                if not in_gap:
                    gap_start = i
                    in_gap = True
            else:
                if in_gap and i - gap_start > 3:
                    row_gaps.append((gap_start + i) // 2)
                    in_gap = False
        
        if len(row_gaps) < 2:
            row_positions = [0, h]
        else:
            row_positions = [0] + row_gaps + [h]
        
        col_proj = np.sum(binary, axis=0)
        col_gaps = []
        in_gap = False
        gap_start = 0
        min_gap_width = w // 20
        
        for i in range(w):
            if col_proj[i] < 5:
                if not in_gap:
                    gap_start = i
                    in_gap = True
            else:
                if in_gap and i - gap_start >= min_gap_width:
                    col_gaps.append((gap_start + i) // 2)
                    in_gap = False
        
        if len(col_gaps) < 2:
            col_positions = [0, w]
        else:
            col_positions = [0] + col_gaps + [w]
        
        return row_positions, col_positions

    def detect_merged_cells(
        self,
        table_img: np.ndarray,
        row_positions: List[int],
        col_positions: List[int]
    ) -> List[List[Dict]]:
        num_rows = len(row_positions) - 1
        num_cols = len(col_positions) - 1
        
        cell_grid = []
        
        for r in range(num_rows):
            row_cells = []
            for c in range(num_cols):
                x = col_positions[c]
                y = row_positions[r]
                w = col_positions[c + 1] - x
                h = row_positions[r + 1] - y
                
                cell_img = table_img[y:y + h, x:x + w]
                
                if len(cell_img.shape) == 3:
                    cell_gray = cv2.cvtColor(cell_img, cv2.COLOR_BGR2GRAY)
                else:
                    cell_gray = cell_img
                
                _, cell_binary = cv2.threshold(cell_gray, 127, 255, cv2.THRESH_BINARY_INV)
                has_content = np.sum(cell_binary) > 100
                
                row_cells.append({
                    "row": r,
                    "col": c,
                    "rowspan": 1,
                    "colspan": 1,
                    "x": x,
                    "y": y,
                    "width": w,
                    "height": h,
                    "has_content": has_content,
                    "merged": False,
                    "is_header": False,
                })
            cell_grid.append(row_cells)
        
        for r in range(num_rows):
            c = 0
            while c < num_cols:
                if not cell_grid[r][c]["merged"]:
                    c += 1
                    continue
                
                end_col = c
                while end_col + 1 < num_cols and cell_grid[r][end_col + 1]["merged"]:
                    end_col += 1
                
                if end_col > c:
                    cell_grid[r][c]["colspan"] = end_col - c + 1
                    for cc in range(c + 1, end_col + 1):
                        cell_grid[r][cc]["merged"] = True
                
                c = end_col + 1
        
        return cell_grid

    def ocr_cell_content(
        self,
        cell_img: np.ndarray,
        lang: str = "chi_sim+eng"
    ) -> str:
        if cell_img.size == 0:
            return ""
        
        try:
            text = pytesseract.image_to_string(cell_img, lang=lang)
            return text.strip()
        except Exception:
            return ""

    def detect_header_row(
        self,
        table_structure: TableStructure,
        table_img: np.ndarray,
        row_positions: List[int]
    ) -> bool:
        if len(row_positions) < 2:
            return False
        
        first_row_height = row_positions[1] - row_positions[0]
        second_row_height = row_positions[2] - row_positions[1] if len(row_positions) > 2 else first_row_height
        
        if first_row_height > second_row_height * 1.2:
            return True
        
        if len(table_structure.cells) > 0:
            first_row_cells = [
                c for c in table_structure.cells if c.row == 0
            ]
            if first_row_cells:
                all_text = "".join(c.content for c in first_row_cells)
                if len(all_text) > 0 and all_text.isupper():
                    return True
        
        return False

    def analyze_table(
        self,
        full_img: np.ndarray,
        table_bbox: Tuple[int, int, int, int],
        perform_ocr: bool = False
    ) -> TableStructure:
        table_img = self.extract_table_image(full_img, table_bbox)
        
        horizontal_lines, vertical_lines = self.detect_table_lines(table_img)
        
        has_borders = (
            np.sum(horizontal_lines) > 1000 and
            np.sum(vertical_lines) > 1000
        )
        
        if has_borders:
            row_positions, col_positions = self.detect_cell_boundaries(
                table_img, horizontal_lines, vertical_lines
            )
        else:
            row_positions, col_positions = self.infer_borderless_table(table_img)
        
        num_rows = len(row_positions) - 1
        num_cols = len(col_positions) - 1
        
        table_structure = TableStructure(
            rows=num_rows,
            cols=num_cols,
        )
        
        for r in range(num_rows):
            for c in range(num_cols):
                x = col_positions[c] + table_bbox[0]
                y = row_positions[r] + table_bbox[1]
                w = col_positions[c + 1] - col_positions[c]
                h = row_positions[r + 1] - row_positions[r]
                
                cell_img = table_img[
                    row_positions[r]:row_positions[r + 1],
                    col_positions[c]:col_positions[c + 1]
                ]
                
                content = ""
                if perform_ocr:
                    content = self.ocr_cell_content(cell_img)
                
                cell = TableCell(
                    row=r,
                    col=c,
                    rowspan=1,
                    colspan=1,
                    content=content,
                    is_header=False,
                    x=x,
                    y=y,
                    width=w,
                    height=h,
                )
                table_structure.cells.append(cell)
        
        table_structure.has_header = self.detect_header_row(
            table_structure, table_img, row_positions
        )
        
        if table_structure.has_header:
            for cell in table_structure.cells:
                if cell.row == 0:
                    cell.is_header = True
        
        return table_structure

    def analyze_tables(
        self,
        full_img: np.ndarray,
        table_bboxes: List[Tuple[int, int, int, int]],
        perform_ocr: bool = False
    ) -> List[TableStructure]:
        results = []
        for bbox in table_bboxes:
            try:
                table = self.analyze_table(full_img, bbox, perform_ocr)
                results.append(table)
            except Exception as e:
                print(f"Error analyzing table at {bbox}: {e}")
        return results
