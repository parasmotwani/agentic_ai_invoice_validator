import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'watcher')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import re
from file_watcher import get_latest_file_in_folder
from pdf2image import convert_from_path
import pytesseract
from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate
import os
import json
from supabase import create_client
from ingestion.gmail_ingestion import check_email_and_upload
from helper.drive_uploader import get_drive_uploader_email

from dotenv import load_dotenv
load_dotenv()




def extract_text_from_image(image_path):
    return pytesseract.image_to_string(image_path)

def extract_text_from_pdf(pdf_path):
    images = convert_from_path(pdf_path)
    texts = [pytesseract.image_to_string(image) for image in images]
    return ' '.join(texts)


llm = OllamaLLM(model="mistral")  # Requires Ollama to be running

prompt_template = PromptTemplate(
    input_variables=["text", "sender_email"],
    template="""
You are an expert at extracting structured data from documents. Given the OCR text from a document, extract and return a JSON with the following fields:

Company Name, Invoice Number, Invoice Date, GSTIN, PAN, HSN/SAC, Taxes, Total Amount, Payment Terms, Currency, Customer Name, Billing Address, Shipping Address, Document Type, Company Address, Received_From.

Received_From = {{sender_email}}

- Only use information explicitly present in the text.
- If a field is not found in the text, set its value to null.
- Do not assume or infer any values.
- The output must be strictly a valid JSON object and nothing else.
- Extract date in the given format yyyy-mm-dd

OCR Text:
{text}

Return only JSON:
Return only a valid JSON object (no explanations, no markdown).
"""
)

chain = prompt_template | llm

def extract_json_from_response(text: str) -> str:
    code_block_match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if not code_block_match:
        code_block_match = re.search(r"```\s*(\{.*?\})\s*```", text, re.DOTALL)
    if code_block_match:
        return code_block_match.group(1)
    json_match = re.search(r"(\{.*\})", text, re.DOTALL)
    if json_match:
        return json_match.group(1)
    # If no JSON found, return original text (likely invalid)
    return text


def extract_fields_with_llm(ocr_text, sender_email):
    result = chain.invoke({"text": ocr_text, "sender_email": sender_email}).strip()
    # If result doesn't start with {
    if not result.startswith('{'):
        result = '{' + result
    if not result.endswith('}'):
        result = result + '}'
    try:
        return json.loads(result)
    except Exception as e:
        return {
            "error": "Failed to parse JSON",
            "exception": str(e),
            "raw_output": result
        }


REQUIRED_FIELDS = [
    "Company Name", "Invoice Number", "Invoice Date", "GSTIN", "PAN", "HSN/SAC", "Taxes",
    "Total Amount", "Payment Terms", "Currency", "Customer Name",
    "Billing Address", "Shipping Address", "Document Type", "Company Address", "Received_From"
]

def enforce_nulls(output_dict):
    if isinstance(output_dict, dict) and "error" not in output_dict:
        return {field: output_dict.get(field, None) for field in REQUIRED_FIELDS}
    return output_dict

def extract_fields(filepath, sender_email):
    if filepath.lower().endswith(('.png', '.jpg', '.jpeg')):
        ocr_text = extract_text_from_image(filepath)
    elif filepath.lower().endswith('.pdf'):
        ocr_text = extract_text_from_pdf(filepath)
    else:
        raise ValueError("Unsupported file type: must be PDF or image.")

    print("\n[INFO] OCR Text \n", ocr_text)
    raw_result = extract_fields_with_llm(ocr_text, sender_email)
    validated_result = enforce_nulls(raw_result)
    return validated_result


supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

def insert_to_supabase(data: dict):
    try:
        if isinstance(data.get("Taxes"), dict):
            data["Taxes"] = json.dumps(data["Taxes"])

        if isinstance(data.get("Billing Address"), dict):
            data["Billing Address"] = json.dumps(data["Billing Address"])
        response = supabase.table("extracted_information").insert([data]).execute()
        print("Successfully inserted data:")
        print(response)
    except Exception as e:
        print("Error inserting data:")
        print(e)
    '''if error:
        print("Error inserting data:", error)
    else:
        print("Successfully inserted data:")
        print(response)'''

def process_latest_invoice():
    filepath, file_id = get_latest_file_in_folder()

    if not filepath:
        print("No file to process.")
        return None, None

    gmail_result = check_email_and_upload()
    if gmail_result:
        file_id, sender_email = gmail_result
        print(f"[INFO] Sender Email from Gmail: {sender_email}")
    else:
        filepath, file_id = get_latest_file_in_folder()
        if file_id:
            sender_email = get_drive_uploader_email(file_id)
            print(f"[INFO] Sender Email from Drive: {sender_email}")
        else:
            print("[ERROR] No file found to process")

    try:
        result = extract_fields(filepath, sender_email)

        if isinstance(result, dict) and "error" not in result:
            result["file_id"] = file_id
            result["Received_From"] = sender_email 
            insert_to_supabase(result)
            print("\n[Validated Result]:\n", json.dumps(result, indent=2))
            return result, file_id
        else:
            print("[ERROR] Invalid invoice format or OCR failed.")
            return None, None

    finally:
        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"[Cleanup] Deleted temp file: {filepath}")




