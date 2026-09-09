AI-Powered Form Builder & Document Autofill

A smart web application that allows users to create custom forms, upload documents, automatically extract relevant information using AI, review and edit the extracted values, and save the completed form.

Features

Dynamic Form Builder

Create form fields dynamically at runtime.

No code changes are required when the form structure changes.

Supported field types:

Single-line text

Multi-line text

Number

Date

Dropdown

Checkbox

Mark fields as required or optional.

Remove fields when they are no longer needed.

Live form preview.

Document Upload

Supports:

PDF

PNG

JPG

JPEG

Validates uploaded files and provides clear success or error messages.

AI-Powered Extraction

Uses the user-created form fields as the extraction schema.

Extracts matching information from uploaded documents.

Dynamically maps extracted values to the appropriate form fields.

Does not rely on hard-coded fields.

Missing or uncertain information is left blank rather than guessed.

Provides extraction confidence information.

Document Processing

Text-based PDFs are processed using PyMuPDF.

Scanned or image-based PDFs can be processed as images.

Image documents can be processed directly.

Review and Validation

Users can review AI-extracted values.

Extracted values can be edited manually.

Required fields are highlighted when empty.

Basic field-type validation is performed before saving.

Save and Export

Save completed form data.

Download the completed form as a PDF.

Download structured form data as JSON.

Tech Stack

Python

Streamlit

Google Gemini API

Google GenAI Python SDK

PyMuPDF

Pillow

ReportLab

python-dotenv

Project Structure

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
└── screenshots/
    ├── 01_form_builder.png
    ├── 02_document_upload.png
    ├── 03_ai_extraction.png
    └── 04_review_save.png

Installation

1. Clone the repository

git clone <repository-url>
cd AI_Powered_Form_Builder

2. Create a virtual environment

For Windows:

python -m venv .venv
.venv\Scripts\activate

3. Install dependencies

pip install -r requirements.txt

4. Configure the API key

Create a .env file in the project root:

GEMINI_API_KEY=your_gemini_api_key

Optional model configuration:

GEMINI_MODEL=gemini-3.8-flash

Keep the .env file private and do not commit it to GitHub.

5. Run the application

streamlit run app.py

The application will open at the local Streamlit URL displayed in the terminal.

How It Works

The user creates a form by adding fields dynamically.

Each field has a label, type, and required/optional setting.

The user uploads a document.

The application processes the document.

Gemini AI extracts information according to the user-defined form schema.

Extracted values are displayed in the form.

The user reviews and edits the values if necessary.

Required fields are validated.

The completed form can be saved and exported.

Schema-Driven Extraction

The application separates the form schema from the extraction logic.

For example, a user can create:

Candidate Name       → Single-line text
Email Address        → Single-line text
Skills               → Multi-line text
Years of Experience  → Number

The same application can also be configured for another use case:

Invoice Number → Single-line text
Invoice Date   → Date
Amount         → Number
Paid           → Checkbox

The extraction logic does not need to be modified when the form fields change.

Missing and Uncertain Values

The application follows a conservative extraction approach:

Missing information is left blank.

Uncertain information is not guessed.

Required empty fields are identified during validation.

Users can manually correct extracted values.

Invalid values are not silently replaced with guessed values.

Error Handling

The application handles common situations such as:

Unsupported file types

Invalid or corrupt documents

Attempting extraction before creating form fields

Missing required values

Invalid field values

Temporary AI service failures

Documents with little or no extractable text

Transient AI service failures are retried, and supported fallback models can be used when necessary.

Screenshots

Dynamic Form Builder



Document Upload



AI Extraction



Review and Save



Design Considerations

The form schema is completely user-driven.

AI extraction is treated as a draft and should be reviewed by the user.

The application prioritizes accuracy and avoids guessing uncertain information.

Local PDF text extraction reduces unnecessary document processing.

Scanned documents are handled using image-based extraction.

Security

API credentials are stored in environment variables.

.env is excluded from version control.

API keys should never be committed to a public repository.

Uploaded documents are used for the application workflow and are not intentionally stored as permanent application data.

Future Improvements

Drag-and-drop field ordering

Reusable form templates

Import and export of form schemas

More detailed field-level confidence indicators

Database-backed submissions

Authentication and multi-user support

Additional document formats
