"""
OCR Module — Owned by: Anurag
Purpose: Take a product label image, return all detected text + positions.

Install first:
    pip install easyocr --break-system-packages

This uses EasyOCR (free, offline). Set to ENGLISH ONLY by default —
combining English + Hindi in one reader noticeably hurts accuracy on
English-only labels (it tries to match every character against both
scripts) and roughly doubles processing time. If your test products
have Hindi text you need to read, switch LANGUAGES below, but expect
a real accuracy/speed trade-off on English text when you do.
"""

import easyocr
from PIL import Image

LANGUAGES = ['en']  # add 'hi' only if you specifically need Hindi text read

# Load once and reuse (loading the model is slow, don't reload per image)
reader = easyocr.Reader(LANGUAGES, gpu=False)

# Resize any image wider than this before OCR — large phone camera photos
# (often 3000-4000px wide) make OCR much slower for no accuracy benefit.
# 1600px is generally plenty to read label text clearly.
MAX_IMAGE_WIDTH = 1600


def _resize_if_needed(image_path: str) -> str:
    """
    If the image is larger than MAX_IMAGE_WIDTH, resize it and save a
    temp copy — speeds up OCR significantly on modern phone photos.
    Returns the path to use (original or resized temp copy).
    """
    img = Image.open(image_path)
    if img.width <= MAX_IMAGE_WIDTH:
        return image_path

    scale = MAX_IMAGE_WIDTH / img.width
    new_size = (MAX_IMAGE_WIDTH, int(img.height * scale))
    resized = img.resize(new_size, Image.LANCZOS)

    resized_path = image_path.rsplit(".", 1)[0] + "_resized." + image_path.rsplit(".", 1)[-1]
    resized.save(resized_path)
    return resized_path


def extract_text_from_image(image_path: str):
    """
    Returns a list of detected text blocks like:
    [
        {"text": "MRP Rs 100", "bbox": [[x1,y1],[x2,y2],[x3,y3],[x4,y4]], "confidence": 0.91},
        ...
    ]
    """
    processed_path = _resize_if_needed(image_path)
    results = reader.readtext(processed_path)

    blocks = []
    for bbox, text, confidence in results:
        blocks.append({
            "text": text,
            "bbox": bbox,          # 4 corner points of the text box
            "confidence": confidence
        })
    return blocks


def get_full_text(blocks):
    """Joins all detected text into one string — used by the rules engine."""
    return " ".join(b["text"] for b in blocks)


def estimate_text_height(bbox):
    """
    Rough font-height estimate in pixels from a bounding box.
    NOTE: pixel height needs to be converted to real-world mm using
    a reference object or known image DPI — this is a TODO for the
    font-size rule check. For the hackathon demo, we can flag text
    that's proportionally very small vs the rest of the label.
    """
    ys = [point[1] for point in bbox]
    return max(ys) - min(ys)


# Quick manual test
if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "test_images/sample1.jpg"
    blocks = extract_text_from_image(path)
    for b in blocks:
        print(f"[{b['confidence']:.2f}] {b['text']}")
    print("\n--- FULL TEXT ---")
    print(get_full_text(blocks))
