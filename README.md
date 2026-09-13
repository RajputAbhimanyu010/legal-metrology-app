# Legal Metrology Compliance Checker — SIH 26034

A local packaged-commodity inspection system that checks label declarations using image-quality checks, fast OCR and a deterministic Legal Metrology rules engine.

## What the application does

- Secure officer/admin login
- Product-label image upload
- Image-quality pre-check
- One-pass cached EasyOCR for fast extraction
- Deterministic compliance checks for configured Legal Metrology requirements
- PASS / WARN / FAIL findings and points-based score
- Original evidence image retained with every scan
- Searchable scan history
- PDF and editable Word reports
- Built-in sample test images

## Run

Install dependencies:

```bash
pip install -r requirements.txt
python backend/auth.py
```

Backend:

```bash
uvicorn backend.main:app --reload
```

Frontend (second terminal):

```bash
streamlit run frontend/app.py
```

Default demo login: `admin / admin123`. Change it before real deployment.

## Scan flow

```text
Uploaded label image
        |
        +--> Image quality pre-check
        |
        +--> One-pass EasyOCR
        |
        +--> Deterministic Legal Metrology rules
        |
        +--> Score + PASS/WARN/FAIL findings
        |
        +--> SQLite scan record + evidence image
        |
        +--> PDF + editable Word report
```

## Included test images

- `test_images/compliant_label.png`
- `test_images/missing_mrp.png`
- `test_images/missing_consumer_care.png`
- `test_images/blurred_label.png`

## Performance note

The OCR path intentionally uses one EasyOCR pass and limits very wide images to 1600 pixels before OCR. The first scan can still take longer because EasyOCR may need to initialize/load its model; subsequent scans reuse the cached reader.

## Important limitation

This is an inspection-assistance/demo system, not a substitute for an enforcement officer or legal determination. OCR can make mistakes, and the configured rules should be re-verified against the current applicable Legal Metrology text before real-world deployment.
