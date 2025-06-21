
# Agentic AI Invoice Validator

An AI-powered, agent-based invoice validation system that automates document ingestion, information extraction via OCR, and intelligent validation using a local LLM. Valid invoices are uploaded to cloud storage, while invalid ones trigger notifications.

## Project Overview

Agentic AI Invoice Validator is built for automating the tedious task of verifying business documents such as invoices, bills, and receipts. It leverages:

- OCR for text extraction
- Rule-based + LLM-powered validation
- Gmail for automatic document ingestion
- Google Drive for ingesting all invoices (valid/invalid)
- Supabase for data logging and monitoring

## Features

- Email Ingestion: Fetches invoice attachments directly from Gmail
- OCR Extraction: Uses pytesseract for accurate text extraction from images and PDFs
- Agentic Validation: LangChain + local LLMs (via Ollama) for few-shot invoice validation
- Auto Flagging: Invalid invoices are flagged and optionally emailed to senders
- Supabase Logging: Stores results in a structured Supabase DB

## How It Works

1. Email attachments are ingested via Gmail to Drive
2. OCR extracts content from invoices
3. Validation agent checks invoice details using rules + LLM
4. If an invoice is valid then the invoice data is pushed to 'invoice_status' table
5. If an invoice is invalid a follow-up mail is sent to the sender
## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/parasmotwani/agentic_ai_invoice_validator.git
cd agentic_ai_invoice_validator
```

### 2. Install Dependencies

It is recommended to use a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```
### 3. Setup Supabase tables

Create two tables 'extracted_information' and 'invoice_status'

```SQL
create table public.extracted_information (
  "Company Name" character varying null default ''::character varying,
  "Invoice Number" character varying null,
  "Invoice Date" date null,
  "GSTIN" character varying null,
  "PAN" character varying null,
  "HSN/SAC" character varying null,
  "Taxes" text null,
  "Total Amount" character varying null,
  "Payment Terms" text null,
  "Currency" text null,
  "Customer Name" text null,
  "Billing Address" text null,
  "Shipping Address" character varying null,
  "Document Type" text null,
  "Company Address" character varying null,
  "flagged" boolean null,
  "Received_From" character varying null,
  file_id character varying not null,
  created_at timestamp with time zone null default (now() AT TIME ZONE 'ist'::text),
  visited boolean null default false,
  constraint extracted_information_pkey primary key (file_id)
) TABLESPACE pg_default;
```

```SQL
create table public.invoice_status (
  "Company_Name" character varying not null default ''::character varying,
  "Invoice_Number" character varying null,
  "Invoice_Date" date null,
  "GSTIN" character varying null,
  "PAN" character varying null,
  "HSN/SAC" character varying null,
  "Taxes" character varying null,
  "Total_Amount" character varying null,
  "Payment_Terms" text null,
  "Currency" text null,
  "Customer_Name" text null,
  "Billing_Address" character varying null,
  "Shipping_Address" character varying null,
  "Company_Address" character varying null,
  "Received_From" character varying null,
  file_id character varying not null,
  created_at timestamp with time zone null default (now() AT TIME ZONE 'utc'::text),
  constraint invoice_status_pkey primary key (file_id)
) TABLESPACE pg_default;
```

### 4. Configure .env

Create a `.env` file in the root directory:

```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
EMAIL_USER=your_gmail_address
EMAIL_PASS=your_gmail_app_password
DRIVE_FOLDER_ID=your_google_drive_folder_id
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_gmail_address
SMTP_PASS=your_gmail_app_password
```

Use Gmail App Passwords, not your actual password.

## Running the Project

```bash
python main.py
```

This will:
- Check Gmail for new invoice attachments
- Extract content using OCR
- Validate invoices using rules + LLM
- Upload valid ones to Drive, flag invalid ones

## Future Enhancements

- Add support for Messenger/WhatsApp ingestion
- LangChain agent feedback loop with few-shot memory
- Better LLM, OpenAI should work the best
- Integrate with secure cloud databases (e.g., Firestore, DynamoDB)
- Build a Streamlit dashboard for validation analytics
- Add PDF-to-JSON structure mapper

## Contact

Made by Paras Motwani  
LinkedIn: https://www.linkedin.com/in/paras-motwani1/  
