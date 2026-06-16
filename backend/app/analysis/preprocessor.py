import cv2
import numpy as np
from PIL import Image
import fitz
import io
import os
from typing import List, Tuple
import uuid

from app.config import settings


class ImagePreprocessor:
    def __init__(self):
        pass

    @staticmethod
    def load_image(image_path: str) -> np.ndarray:
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"无法加载图像: {image_path}")
        return img

    @staticmethod
    def to_grayscale(img: np.ndarray) -> np.ndarray:
        if len(img.shape) == 3:
            return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return img

    @staticmethod
    def adaptive_binarize(img: np.ndarray) -> np.ndarray:
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img
        binary = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            25, 10
        )
        return binary

    @staticmethod
    def detect_skew_angle(img: np.ndarray) -> float:
        gray = ImagePreprocessor.to_grayscale(img)
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        
        lines = cv2.HoughLinesP(
            edges, 1, np.pi / 180,
            threshold=100,
            minLineLength=100,
            maxLineGap=10
        )
        
        if lines is None or len(lines) == 0:
            return 0.0
        
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
            if abs(angle) < 45:
                angles.append(angle)
        
        if not angles:
            return 0.0
        
        median_angle = np.median(angles)
        return float(median_angle)

    @staticmethod
    def rotate_image(img: np.ndarray, angle: float) -> np.ndarray:
        if abs(angle) < 0.1:
            return img
        
        (h, w) = img.shape[:2]
        center = (w // 2, h // 2)
        
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        
        cos_abs = abs(M[0, 0])
        sin_abs = abs(M[0, 1])
        new_w = int(h * sin_abs + w * cos_abs)
        new_h = int(h * cos_abs + w * sin_abs)
        
        M[0, 2] += (new_w - w) / 2
        M[1, 2] += (new_h - h) / 2
        
        rotated = cv2.warpAffine(
            img, M, (new_w, new_h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(255, 255, 255)
        )
        
        return rotated

    @staticmethod
    def denoise(img: np.ndarray) -> np.ndarray:
        if len(img.shape) == 2:
            return cv2.medianBlur(img, 3)
        return cv2.medianBlur(img, 3)

    @classmethod
    def preprocess(cls, img: np.ndarray, manual_angle: float = None) -> Tuple[np.ndarray, float]:
        if manual_angle is not None:
            angle = manual_angle
        else:
            angle = cls.detect_skew_angle(img)
        
        rotated = cls.rotate_image(img, angle)
        denoised = cls.denoise(rotated)
        
        return denoised, angle

    @classmethod
    def process_pdf(cls, pdf_path: str) -> List[str]:
        doc = fitz.open(pdf_path)
        image_paths = []
        
        task_dir = os.path.dirname(pdf_path)
        os.makedirs(task_dir, exist_ok=True)
        
        for page_num in range(min(len(doc), settings.max_pages)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img_data = pix.tobytes("png")
            
            img_path = os.path.join(task_dir, f"page_{page_num + 1:04d}.png")
            with open(img_path, "wb") as f:
                f.write(img_data)
            image_paths.append(img_path)
        
        doc.close()
        return image_paths

    @staticmethod
    def save_image(img: np.ndarray, output_path: str) -> str:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        cv2.imwrite(output_path, img)
        return output_path

    @staticmethod
    def get_image_size(image_path: str) -> Tuple[int, int]:
        img = Image.open(image_path)
        return img.width, img.height
