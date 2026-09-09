from pathlib import Path

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
MAX_FILE_SIZE_MB = 50


def validate_file(uploaded_file):
    if uploaded_file is None:
        return False, "Please upload a PDF, PNG, JPG, or JPEG file."

    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        return False, f"Unsupported file type: {suffix or 'unknown'}. Allowed: PDF, PNG, JPG, JPEG."

    if uploaded_file.size == 0:
        return False, "The uploaded file is empty or corrupted."

    if uploaded_file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
        return False, f"File is too large. Maximum supported size is {MAX_FILE_SIZE_MB} MB."

    # Basic corruption check before sending to Gemini.
    if suffix == ".pdf":
        try:
            import fitz
            doc = fitz.open(stream=uploaded_file.getvalue(), filetype="pdf")
            if len(doc) == 0:
                return False, "The PDF appears to be corrupted or contains no pages."
            doc.close()
        except Exception:
            return False, "The PDF appears to be corrupted. Please upload a valid PDF."
    else:
        try:
            from PIL import Image
            import io
            image = Image.open(io.BytesIO(uploaded_file.getvalue()))
            image.verify()
        except Exception:
            return False, "The image appears to be corrupted. Please upload a valid PNG/JPG/JPEG image."

    return True, ""


def prepare_document(uploaded_file):
    suffix = Path(uploaded_file.name).suffix.lower()
    file_bytes = uploaded_file.getvalue()

    if suffix == ".pdf":
        return {
            "kind": "pdf",
            "bytes": file_bytes,
            "filename": uploaded_file.name,
        }

    mime = "image/png" if suffix == ".png" else "image/jpeg"
    return {
        "kind": "images",
        "images": [(file_bytes, mime)],
        "filename": uploaded_file.name,
    }
