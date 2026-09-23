"""Run OCR against all sample images."""
import glob
from ocr.extract_text import extract_text_from_image, get_full_text

for path in glob.glob('test_images/*'):
    if not path.lower().endswith(('.png','.jpg','.jpeg')):
        continue
    print(f"\n=== {path} ===")
    blocks = extract_text_from_image(path)
    print(get_full_text(blocks))
    print(f"Blocks: {len(blocks)} | Avg confidence: {sum(b['confidence'] for b in blocks)/len(blocks):.2f}" if blocks else 'No blocks detected')
