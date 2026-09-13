"""Image preprocessing helpers for difficult packaged-label photos."""
from typing import List
import cv2
import numpy as np


def load_image(path: str, max_width: int = 2200) -> np.ndarray:
    data = np.fromfile(path, dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Could not decode image: {path}")
    h, w = image.shape[:2]
    if w > max_width:
        scale = max_width / w
        image = cv2.resize(image, (max_width, int(h * scale)), interpolation=cv2.INTER_AREA)
    return image


def make_variants(image: np.ndarray) -> List[np.ndarray]:
    """Return several non-destructive OCR-friendly variants."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    denoise = cv2.fastNlMeansDenoising(clahe, None, 7, 7, 21)
    adaptive = cv2.adaptiveThreshold(
        denoise, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 11
    )
    up = cv2.resize(image, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
    up_gray = cv2.cvtColor(up, cv2.COLOR_BGR2GRAY)
    up_gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(up_gray)
    sharpen = cv2.detailEnhance(image, sigma_s=10, sigma_r=0.15)
    return [image, clahe, denoise, adaptive, up, up_gray, sharpen]
