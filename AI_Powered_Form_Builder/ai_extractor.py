import io
import json
import os
import re
import time

from google import genai
from google.genai import types


def get_api_key():
    try:
        import streamlit as st
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
    return os.getenv("GEMINI_API_KEY")


def get_model():
    try:
        import streamlit as st
        if "GEMINI_MODEL" in st.secrets:
            return st.secrets["GEMINI_MODEL"]
    except Exception:
        pass
    return os.getenv("GEMINI_MODEL", "gemini-3.8-flash")


def _model_candidates():
    preferred = get_model()
    # Try the configured model first, then stable fallbacks. This prevents a
    # temporary 503/429 on one Gemini model from breaking the whole demo.
    candidates = ["gemini-3.8-flash", preferred, "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash"]
    result = []
    for model in candidates:
        if model and model not in result:
            result.append(model)
    return result


def _strip_code_fence(text: str) -> str:
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _build_prompt(fields):
    schema = [
        {
            "id": f["id"],
            "label": f["label"],
            "type": f["type"],
            "required": f["required"],
            "options": f.get("options", []),
        }
        for f in fields
    ]

    return f"""
You are the AI extraction engine for a dynamic form builder.

The USER-CREATED FORM SCHEMA below is authoritative. It can describe a resume,
job application, invoice, medical intake, or any other document. Do not assume
fixed fields and do not add fields that are not in the schema.

FORM SCHEMA:
{json.dumps(schema, indent=2)}

DOCUMENT CONTENT:
Use only the document content supplied below. Extract values that are actually
supported by it. Never guess.

Return ONLY valid JSON in this exact structure:
{{
  "values": {{ "field_id": value_or_null }},
  "confidence": {{ "field_id": "High|Medium|Low" }},
  "missing_reasons": {{ "field_id": "short reason or empty string" }}
}}

Rules:
1. Include every field id exactly once.
2. If a value is missing, ambiguous, or uncertain, return null. NEVER guess.
3. Number fields must be JSON numbers.
4. Date fields must use YYYY-MM-DD only when clear; otherwise null.
5. Dropdown values must exactly match one supplied option; otherwise null.
6. Checkbox values must be true/false only when clearly supported; otherwise null.
7. Text values should be concise and faithful to the document.
8. Null values must have Low confidence.
9. Confidence describes extraction certainty, not whether a field is required.
""".strip()


def _parse_result(raw, fields):
    raw = _strip_code_fence(raw)
    try:
        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if not match:
            raise RuntimeError("Gemini returned invalid JSON. Please try extraction again.") from exc
        try:
            result = json.loads(match.group(0))
        except json.JSONDecodeError as exc2:
            raise RuntimeError("Gemini returned invalid JSON. Please try extraction again.") from exc2

    values = result.get("values", {}) or {}
    confidence = result.get("confidence", {}) or {}
    reasons = result.get("missing_reasons", {}) or {}

    normalized = {}
    for field in fields:
        fid = field["id"]
        value = values.get(fid)
        conf = confidence.get(fid, "Low" if value is None else "Medium")
        if conf not in {"High", "Medium", "Low"}:
            conf = "Low" if value is None else "Medium"
        normalized[fid] = {
            "value": value,
            "confidence": conf,
            "missing_reason": reasons.get(fid, "") if value is None else "",
        }
    return normalized


def _extract_pdf_text(pdf_bytes):
    try:
        import fitz
        pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages = []
        for page in pdf:
            text = page.get_text("text")
            if text and text.strip():
                pages.append(text.strip())
        pdf.close()
        return "\n\n--- PAGE BREAK ---\n\n".join(pages).strip()
    except Exception:
        return ""


def _generate(client, model, prompt, document):
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
    )

    if document["kind"] == "pdf":
        text = _extract_pdf_text(document["bytes"])
        if text:
            # Keep a reasonable bound for very large documents while preserving
            # the beginning where resumes/forms usually contain key details.
            text = text[:180000]
            contents = [prompt, "\n\nDOCUMENT TEXT:\n", text]
        else:
            # Scanned/image-only PDF fallback: send rendered page images.
            import fitz
            pdf = fitz.open(stream=document["bytes"], filetype="pdf")
            images = []
            for i in range(min(6, len(pdf))):
                page = pdf[i]
                pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
                images.append(pix.tobytes("png"))
            pdf.close()
            contents = [prompt]
            for raw in images:
                from PIL import Image
                contents.append(Image.open(io.BytesIO(raw)))
    else:
        from PIL import Image
        for raw_bytes, _mime in document["images"]:
            image = Image.open(io.BytesIO(raw_bytes))
            contents = [prompt, image]
            break
        else:
            raise RuntimeError("No readable image was found in the uploaded document.")

    return client.models.generate_content(
        model=model,
        contents=contents,
        config=config,
    )


def extract_values(fields, document):
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured. Add your Gemini API key to .env."
        )

    client = genai.Client(api_key=api_key)
    prompt = _build_prompt(fields)
    errors = []

    for model in _model_candidates():
        for attempt in range(2):
            try:
                response = _generate(client, model, prompt, document)
                return _parse_result(response.text, fields)
            except Exception as exc:
                message = str(exc)
                errors.append(f"{model}: {message[:180]}")
                lowered = message.lower()
                transient = any(code in lowered for code in ("503", "429", "unavailable", "resource_exhausted", "high demand", "temporarily"))
                if not transient:
                    break
                if attempt == 0:
                    time.sleep(2)

    raise RuntimeError(
        "Gemini is temporarily unavailable. The app tried multiple stable Gemini models. "
        "Please click Extract & Autofill again in a few seconds."
    )
