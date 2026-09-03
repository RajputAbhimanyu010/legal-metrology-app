"""
OCR Module — Owned by: Anurag
Purpose: Take a product label image, return all detected text + positions.

Install first:
    pip install easyocr --break-system-packages

This uses EasyOCR (free, offline, supports English + Hindi).
"""

import easyocr

# Load once and reuse (loading the model is slow, don't reload per image)
reader = easyocr.Reader(['en', 'hi'], gpu=False)


def extract_text_from_image(image_path: str):
    """
    Returns a list of detected text blocks like:
    [
        {"text": "MRP Rs 100", "bbox": [[x1,y1],[x2,y2],[x3,y3],[x4,y4]], "confidence": 0.91},
        ...
    ]
    """
    results = reader.readtext(image_path)

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
