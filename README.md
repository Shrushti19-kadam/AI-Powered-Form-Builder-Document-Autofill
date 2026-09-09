AI-Powered Form Builder & Document Autofill

An AI-powered web application for creating dynamic forms and automatically filling them with information extracted from uploaded documents.

The application allows users to build a custom form, upload a PDF or image, extract relevant information using AI, review and edit the results, validate the form, and export the completed data.

✨ Features

🧩 Dynamic Form Builder

Create form fields dynamically at runtime.

No source-code changes are required when the form structure changes.

Supports:

Single-line text

Multi-line text

Number

Date

Dropdown

Checkbox

Set fields as Required or Optional.

Remove fields easily.

Live form preview.

📄 Document Upload

Supports PDF, PNG, JPG, and JPEG files.

Validates uploaded documents.

Displays clear success and error messages.

🤖 AI-Powered Document Extraction

Uses Google Gemini for intelligent information extraction.

Extraction is completely schema-driven.

The AI uses the fields created by the user as the extraction schema.

Extracted values are automatically mapped to the corresponding form fields.

Missing or uncertain information is left blank instead of being guessed.

Provides extraction confidence information.

🔍 Document Processing

Text-based PDFs are processed locally using PyMuPDF.

Scanned/image-based PDFs are processed using image extraction.

Image files can be processed directly.

✏️ Review & Validation

Review extracted information before saving.

Edit any extracted value manually.

Required fields are highlighted when empty.

Basic type validation is applied before saving.

Users remain in control of the final submitted information.

💾 Save & Export

Save the completed form.

Download the final form as PDF.

Download structured form data as JSON.

🛠️ Tech Stack

Technology

Purpose

Python

Application logic

Streamlit

Web application UI

Google Gemini

AI-powered extraction

google-genai

Gemini API integration

PyMuPDF

PDF text extraction and rendering

Pillow

Image processing

ReportLab

PDF generation

python-dotenv

Environment variable management

📁 Project Structure

AI_Powered_Form_Builder/
│
├── app.py
├── ai_extractor.py
├── document_utils.py
├── requirements.txt
├── README.md
├── .env.example
├── .gitignore
│
├── .streamlit/
│   └── config.toml
│
└── Screenshots/
    ├── AI_Extraction.png
    ├── Downloaded_PDF.png
    ├── Saved_PDF.png
    ├── Upload_Resume.png
    └── form_builder.png

🚀 Installation & Setup

1. Clone the repository

1. Clone the repository

git clone https://github.com/Shrushti19-kadam/AI-Powered-Form-Builder-Document-Autofill.git
cd AI_Powered_Form_Builder

2. Create a virtual environment

Windows:

python -m venv .venv
.venv\Scripts\activate

3. Install dependencies

pip install -r requirements.txt

4. Configure Gemini API

Create a .env file in the project root:

GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.6-flash

Keep your actual API key private. Never commit .env to the repository.

5. Run the application

streamlit run app.py

The application will open using the local Streamlit URL displayed in the terminal.

🔄 Application Workflow

Create Form
     ↓
Add Dynamic Fields
     ↓
Upload Document
     ↓
AI Extraction
     ↓
Autofill Form
     ↓
Review & Edit
     ↓
Validate Required Fields
     ↓
Save & Export

Step-by-step

Create the required form fields.

Select the field type for each field.

Choose whether each field is required or optional.

Upload a PDF or image document.

Click Extract & Autofill.

Review the extracted information.

Edit incorrect or missing values.

Complete all required fields.

Save the final form.

Download the PDF or JSON output.

🧠 Schema-Driven Architecture

The application keeps the form schema separate from the AI extraction logic.

For example:

Candidate Name       → Text
Email Address        → Text
Skills               → Multi-line Text
Years of Experience  → Number

The same application can be configured for a completely different form:

Invoice Number → Text
Invoice Date   → Date
Amount         → Number
Paid           → Checkbox

No changes to the extraction code are required when the form fields change.

🛡️ Handling Missing & Uncertain Information

The application follows a conservative extraction strategy:

Missing values remain blank.

Uncertain values are not guessed.

Required empty fields are identified during validation.

Users can manually correct extracted information.

Invalid values are not silently replaced with guessed values.

This helps keep the final form reviewable and reliable.

⚠️ Error Handling

The application handles common cases such as:

Unsupported file types

Invalid or corrupt documents

Extraction attempted before creating fields

Missing required values

Invalid field values

Temporary AI service failures

Documents with little or no extractable text

Transient AI service failures are retried, with supported fallback models available when necessary.

📸 Screenshots

Dynamic Form Builder



Document Upload



AI Extraction



Saved Form



Downloaded PDF



🔐 Security

API credentials are stored using environment variables.

.env is excluded from version control.

API keys should never be committed to a public repository.

Uploaded documents are used for the application workflow and are not intentionally stored as permanent application data.

🔮 Future Improvements

Drag-and-drop field reordering

Reusable form templates

Form schema import/export

More detailed field-level confidence indicators

Database-backed submissions

Authentication and multi-user support

Additional document formats

Cloud deployment

📌 Key Highlights

Fully dynamic form creation

Schema-driven AI extraction

PDF and image document support

AI-assisted autofill

Human review and editing

Required-field validation

PDF and JSON export

Error handling and fallback extraction
