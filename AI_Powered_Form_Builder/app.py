import json
import re
import uuid
from datetime import date, datetime
from pathlib import Path
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

import streamlit as st
from dotenv import load_dotenv

from ai_extractor import extract_values
from document_utils import prepare_document, validate_file

load_dotenv()

st.set_page_config(
    page_title="AI-Powered Form Builder & Document Autofill",
    page_icon="🧠",
    layout="wide",
)

# -----------------------------
# Session state
# -----------------------------
if "fields" not in st.session_state:
    st.session_state.fields = []

if "form_values" not in st.session_state:
    st.session_state.form_values = {}

if "uploaded_name" not in st.session_state:
    st.session_state.uploaded_name = None

if "extraction_done" not in st.session_state:
    st.session_state.extraction_done = False

if "saved_payload" not in st.session_state:
    st.session_state.saved_payload = None
if "saved_pdf_bytes" not in st.session_state:
    st.session_state.saved_pdf_bytes = None
if "saved_json_bytes" not in st.session_state:
    st.session_state.saved_json_bytes = None
if "saved_pdf_filename" not in st.session_state:
    st.session_state.saved_pdf_filename = None
if "saved_json_filename" not in st.session_state:
    st.session_state.saved_json_filename = None


FIELD_TYPES = [
    "Single-line text",
    "Multi-line text",
    "Number",
    "Date",
    "Dropdown",
    "Checkbox",
]


def slugify(text):
    value = re.sub(r"[^a-zA-Z0-9]+", "_", text.strip().lower()).strip("_")
    return value or f"field_{uuid.uuid4().hex[:6]}"


def add_field(label, field_type, required, options):
    base = slugify(label)
    existing = {f["id"] for f in st.session_state.fields}
    field_id = base
    counter = 2
    while field_id in existing:
        field_id = f"{base}_{counter}"
        counter += 1

    st.session_state.fields.append(
        {
            "id": field_id,
            "label": label.strip(),
            "type": field_type,
            "required": required,
            "options": options,
        }
    )
    st.session_state.extraction_done = False
    st.session_state.saved_payload = None
    st.session_state.saved_pdf_bytes = None
    st.session_state.saved_json_bytes = None


def remove_field(field_id):
    st.session_state.fields = [
        field for field in st.session_state.fields if field["id"] != field_id
    ]
    st.session_state.form_values.pop(field_id, None)
    st.session_state.saved_payload = None
    st.session_state.saved_pdf_bytes = None
    st.session_state.saved_json_bytes = None


def coerce_value(field, value):
    if value is None:
        return None

    ftype = field["type"]
    if ftype == "Number":
        try:
            return float(value) if "." in str(value) else int(value)
        except (ValueError, TypeError):
            return value

    if ftype == "Checkbox":
        return bool(value)

    return str(value)


def render_field(field, key_prefix):
    fid = field["id"]
    label = field["label"]
    required = field["required"]
    current = st.session_state.form_values.get(fid)

    missing_required = required and (current is None or current == "")

    if missing_required:
        st.warning(f"Required field: **{label}** still needs a value.")

    help_text = "Required field" if required else "Optional field"

    if field["type"] == "Single-line text":
        return st.text_input(
            label + (" *" if required else ""),
            value="" if current is None else str(current),
            key=f"{key_prefix}_{fid}",
            help=help_text,
        )

    if field["type"] == "Multi-line text":
        return st.text_area(
            label + (" *" if required else ""),
            value="" if current is None else str(current),
            key=f"{key_prefix}_{fid}",
            help=help_text,
        )

    if field["type"] == "Number":
        raw = st.text_input(
            label + (" *" if required else ""),
            value="" if current is None else str(current),
            key=f"{key_prefix}_{fid}",
            help="Enter a number.",
        )
        if raw.strip() == "":
            return None
        try:
            return float(raw) if "." in raw else int(raw)
        except ValueError:
            st.error(f"{label}: please enter a valid number.")
            return raw

    if field["type"] == "Date":
        return st.text_input(
            label + (" *" if required else ""),
            value="" if current is None else str(current),
            placeholder="YYYY-MM-DD",
            key=f"{key_prefix}_{fid}",
            help="Use YYYY-MM-DD when possible.",
        )

    if field["type"] == "Dropdown":
        options = field.get("options", [])
        choices = [""] + options
        current_index = choices.index(current) if current in choices else 0
        selected = st.selectbox(
            label + (" *" if required else ""),
            choices,
            index=current_index,
            key=f"{key_prefix}_{fid}",
        )
        return selected or None

    if field["type"] == "Checkbox":
        return st.checkbox(
            label + (" *" if required else ""),
            value=bool(current) if current is not None else False,
            key=f"{key_prefix}_{fid}",
        )

    return current


def validate_final_values():
    errors = []
    for field in st.session_state.fields:
        value = st.session_state.form_values.get(field["id"])
        if field["required"] and (value is None or value == ""):
            errors.append(field["label"])

        if field["type"] == "Date" and value:
            try:
                datetime.strptime(str(value), "%Y-%m-%d")
            except ValueError:
                errors.append(f"{field['label']} (invalid date; use YYYY-MM-DD)")

        if field["type"] == "Number" and value not in (None, ""):
            try:
                float(value)
            except (ValueError, TypeError):
                errors.append(f"{field['label']} (invalid number)")

    return errors


def save_submission():
    Path("saved_submissions").mkdir(exist_ok=True)
    payload = {
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "document": st.session_state.uploaded_name,
        "fields": st.session_state.fields,
        "values": st.session_state.form_values,
    }
    filename = datetime.now().strftime("submission_%Y%m%d_%H%M%S.json")
    path = Path("saved_submissions") / filename
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return payload, filename


def create_form_pdf(payload):
    """Create a simple PDF containing the final saved form values."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Final Submitted Form", styles["Title"]),
        Spacer(1, 12),
    ]

    from xml.sax.saxutils import escape

    normal_style = styles["Normal"].clone("FormTableNormal")
    normal_style.fontName = "Helvetica"
    normal_style.fontSize = 9
    normal_style.leading = 12
    normal_style.wordWrap = "LTR"

    header_style = styles["Normal"].clone("FormTableHeader")
    header_style.fontName = "Helvetica-Bold"
    header_style.fontSize = 9
    header_style.leading = 12

    # Use Paragraphs inside table cells so long values (especially Skills)
    # automatically wrap onto multiple lines instead of overflowing.
    rows = [[Paragraph("Field", header_style), Paragraph("Value", header_style)]]
    for field in payload["fields"]:
        value = payload["values"].get(field["id"])
        if value is None or value == "":
            display_value = "Not provided"
        elif isinstance(value, bool):
            display_value = "Yes" if value else "No"
        else:
            display_value = str(value)

        label_text = escape(str(field["label"]))
        value_text = escape(display_value).replace("\n", "<br/>")
        rows.append([
            Paragraph(label_text, normal_style),
            Paragraph(value_text, normal_style),
        ])

    table = Table(rows, colWidths=[150, 330], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(table)
    story.append(Spacer(1, 14))
    story.append(Paragraph(
        f"Source document: {payload.get('document') or 'Not provided'}<br/>"
        f"Saved at: {payload['saved_at']}",
        styles["Normal"],
    ))
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# -----------------------------
# UI — Dashboard
# -----------------------------
st.markdown("""
<style>
.block-container {padding-top: 2rem; padding-bottom: 3rem;}
.dashboard-hero {
    padding: 1.4rem 1.6rem;
    border-radius: 18px;
    background: linear-gradient(135deg, #f7f8ff 0%, #eef4ff 100%);
    border: 1px solid #dfe6f3;
    margin-bottom: 1.2rem;
}
.dashboard-hero h1 {margin: 0; font-size: 2.2rem;}
.dashboard-hero p {margin: .35rem 0 0; color: #5f6b7a; font-size: 1rem;}
.metric-card {
    padding: 1rem 1.1rem;
    border-radius: 14px;
    background: white;
    border: 1px solid #e4e8ef;
    min-height: 105px;
    box-shadow: 0 2px 10px rgba(20, 30, 50, .04);
}
.metric-label {color: #697586; font-size: .82rem; margin-bottom: .35rem;}
.metric-value {font-size: 1.55rem; font-weight: 700; color: #172033;}
.step-card {
    padding: .85rem 1rem;
    border-radius: 12px;
    border: 1px solid #e4e8ef;
    background: #fff;
    text-align: center;
    min-height: 82px;
}
.step-number {font-weight: 700; font-size: .82rem; color: #53657d;}
.step-title {font-weight: 650; margin-top: .25rem;}
</style>

<div class="dashboard-hero">
    <h1>🧠 AI-Powered Form Builder & Document Autofill</h1>
    <p>Build a custom form, extract information from documents with AI, review the results, and save a polished final submission.</p>
</div>
""", unsafe_allow_html=True)

# Dashboard summary
field_count = len(st.session_state.fields)
doc_status = "Uploaded" if st.session_state.uploaded_name else "Waiting"
extract_status = "Completed" if st.session_state.get("extraction_done") else "Not started"
required_count = sum(1 for f in st.session_state.fields if f.get("required"))

metric_cols = st.columns(4)
metrics = [
    ("Fields configured", str(field_count)),
    ("Required fields", str(required_count)),
    ("Document", doc_status),
    ("AI extraction", extract_status),
]
for col, (label_text, value_text) in zip(metric_cols, metrics):
    with col:
        st.markdown(
            f'<div class="metric-card"><div class="metric-label">{label_text}</div>'
            f'<div class="metric-value">{value_text}</div></div>',
            unsafe_allow_html=True,
        )

st.write("")
step_cols = st.columns(3)
steps = [("STEP 1", "Build your form"), ("STEP 2", "Upload & extract"), ("STEP 3", "Review & save")]
for col, (number, title) in zip(step_cols, steps):
    with col:
        st.markdown(
            f'<div class="step-card"><div class="step-number">{number}</div>'
            f'<div class="step-title">{title}</div></div>',
            unsafe_allow_html=True,
        )

st.write("")

with st.sidebar:
    st.header("1. Build Your Form")
    st.caption("All fields are created at runtime; there are no hardcoded form fields.")

    with st.form("add_field_form", clear_on_submit=True):
        label = st.text_input("Field label", placeholder="e.g. Candidate Name")
        field_type = st.selectbox("Field type", FIELD_TYPES)
        required = st.checkbox("Required field")
        options_text = ""
        if field_type == "Dropdown":
            options_text = st.text_input(
                "Dropdown options",
                placeholder="Python, Java, JavaScript",
                help="Separate options with commas.",
            )

        add_clicked = st.form_submit_button("➕ Add Field", use_container_width=True)

        if add_clicked:
            if not label.strip():
                st.error("Field label is required.")
            else:
                options = (
                    [item.strip() for item in options_text.split(",") if item.strip()]
                    if field_type == "Dropdown"
                    else []
                )
                if field_type == "Dropdown" and not options:
                    st.error("Add at least one dropdown option.")
                else:
                    add_field(label, field_type, required, options)
                    st.rerun()

    if st.session_state.fields:
        st.divider()
        st.subheader("Configured Fields")

        for index, field in enumerate(st.session_state.fields):
            c1, c2 = st.columns([5, 1])
            with c1:
                st.write(
                    f"**{index + 1}. {field['label']}** — {field['type']}"
                    + (" — Required" if field["required"] else " — Optional")
                )
            with c2:
                if st.button("🗑️", key=f"remove_{field['id']}"):
                    remove_field(field["id"])
                    st.rerun()

    if st.button("Clear Form", use_container_width=True):
        st.session_state.fields = []
        st.session_state.form_values = {}
        st.session_state.extraction_done = False
        st.session_state.saved_payload = None
        st.session_state.saved_pdf_bytes = None
        st.session_state.saved_json_bytes = None
        st.rerun()

# -----------------------------
# Live preview
# -----------------------------
st.header("Live Form Preview")

if not st.session_state.fields:
    st.info("No fields yet. Use the sidebar to create your form.")
else:
    st.success(f"{len(st.session_state.fields)} field(s) configured.")
    # Read-only live preview.
    # Do NOT write preview values back into form_values; otherwise the
    # preview widgets can overwrite AI-extracted values before review.
    preview_cols = st.columns(2)
    for index, field in enumerate(st.session_state.fields):
        with preview_cols[index % 2]:
            value = st.session_state.form_values.get(field["id"])
            display_value = "Not filled yet" if value in (None, "") else value
            if isinstance(value, bool):
                display_value = "Yes" if value else "No"
            st.markdown(f"**{field['label']}**" + (" *" if field["required"] else ""))
            st.write(display_value)

# -----------------------------
# Document upload
# -----------------------------
st.divider()
st.header("2. Upload Document")

if not st.session_state.fields:
    st.warning("Build the form first, then upload a document.")

uploaded_file = st.file_uploader(
    "Upload PDF, PNG, JPG, or JPEG",
    type=["pdf", "png", "jpg", "jpeg"],
    disabled=not bool(st.session_state.fields),
)

if uploaded_file is not None:
    valid, error = validate_file(uploaded_file)
    if not valid:
        st.error(error)
        st.session_state.uploaded_name = None
    else:
        st.success(f"Uploaded successfully: **{uploaded_file.name}**")
        st.session_state.uploaded_name = uploaded_file.name

        if st.button("🤖 Extract & Autofill", type="primary", use_container_width=True):
            try:
                with st.spinner("Reading the document and extracting form values..."):
                    document = prepare_document(uploaded_file)
                    extracted = extract_values(st.session_state.fields, document)

                st.session_state.form_values = {
                    field["id"]: extracted[field["id"]]["value"]
                    for field in st.session_state.fields
                }
                st.session_state.extraction_meta = extracted
                st.session_state.extraction_done = True
                st.session_state.saved_payload = None
                st.session_state.saved_pdf_bytes = None
                st.session_state.saved_json_bytes = None
                st.success("Extraction completed. Review and edit the values below.")
                st.rerun()

            except Exception as exc:
                st.error(f"Extraction failed: {exc}")

# -----------------------------
# Review / edit / save
# -----------------------------
if st.session_state.get("extraction_done"):
    st.divider()
    st.header("3. Review, Edit & Save")

    meta = st.session_state.get("extraction_meta", {})

    for index, field in enumerate(st.session_state.fields):
        fid = field["id"]
        item = meta.get(fid, {})
        confidence = item.get("confidence", "Low")
        missing_reason = item.get("missing_reason", "")

        if st.session_state.form_values.get(fid) in (None, ""):
            if field["required"]:
                st.error(f"⚠️ Required field **{field['label']}** is blank.")
            else:
                st.info(f"ℹ️ **{field['label']}** was not found in the document.")
            if missing_reason:
                st.caption(f"Reason: {missing_reason}")

        st.caption(f"AI confidence: {confidence}")

    st.subheader("Edit extracted values")
    edit_cols = st.columns(2)
    for index, field in enumerate(st.session_state.fields):
        with edit_cols[index % 2]:
            new_value = render_field(field, "edit")
            st.session_state.form_values[field["id"]] = new_value

    errors = validate_final_values()
    if errors:
        st.warning("Complete/fix these fields before saving:")
        for error in errors:
            st.write(f"- {error}")
    else:
        st.success("All required fields are complete and valid.")

    if st.button(
        "💾 Save Final Form",
        type="primary",
        use_container_width=True,
        disabled=bool(errors),
    ):
        payload, filename = save_submission()
        pdf_bytes = create_form_pdf(payload)
        pdf_filename = Path(filename).with_suffix(".pdf").name
        json_bytes = json.dumps(payload, indent=2, default=str).encode("utf-8")

        st.session_state.saved_payload = payload
        st.session_state.saved_pdf_bytes = pdf_bytes
        st.session_state.saved_json_bytes = json_bytes
        st.session_state.saved_pdf_filename = pdf_filename
        st.session_state.saved_json_filename = filename
        st.success(f"✅ Final form saved successfully as `{filename}`.")

    if st.session_state.saved_payload is not None:
        st.subheader("Download Saved Form")
        st.download_button(
            "📄 Download Final Form (PDF)",
            data=st.session_state.saved_pdf_bytes,
            file_name=st.session_state.saved_pdf_filename,
            mime="application/pdf",
            use_container_width=True,
            key="download_final_pdf",
        )
        st.download_button(
            "⬇️ Download Submission Data (JSON)",
            data=st.session_state.saved_json_bytes,
            file_name=st.session_state.saved_json_filename,
            mime="application/json",
            use_container_width=True,
            key="download_submission_json",
        )

# -----------------------------
# Current schema
# -----------------------------
with st.expander("View Current Form Schema"):
    st.json(st.session_state.fields)
