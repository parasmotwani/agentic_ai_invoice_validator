from langchain.tools import tool
from supabase import create_client
import os, json
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
load_dotenv()

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

@tool
def update_flagged(tool_input: str) -> str:
    """
    Update the 'flagged' and 'visited' status of a document based on validation result.
    
    Args:
        tool_input: JSON string with format: {"file_id": "string", "is_valid": boolean}
        Example: '{"file_id": "1mvyL6WyMjZsIIq5tWkHJwQQ9-0kkgtJJ", "is_valid": false}'
    """
    try:
        # Parse the input - handle both string and dict inputs
        if isinstance(tool_input, str):
            # Try to parse as JSON first
            try:
                data = json.loads(tool_input)
            except json.JSONDecodeError:
                # If not JSON, assume it's just a file_id and default is_valid to False
                data = {"file_id": tool_input.strip("'\""), "is_valid": False}
        else:
            data = tool_input
        
        file_id = data["file_id"].strip("'\"")  # Remove any extra quotes
        is_valid = data.get("is_valid", False)  # Default to False if not provided
        
        # Update Supabase
        result = supabase.table("extracted_information").update({
            "flagged": not is_valid,  # flagged=True means invalid, flagged=False means valid
            "visited": True
        }).eq("file_id", file_id).execute()
        
        return f"Successfully updated: flagged={not is_valid}, visited=True for file_id={file_id}"
        
    except Exception as e:
        return f"Error updating flagged status: {str(e)}"

@tool
def fetch_other_invoices(file_id: str) -> str:
    """Get all invoices except the current one."""
    try:
        file_id = file_id.strip("'\"")  # Remove any extra quotes
        result = supabase.table("extracted_information").select("*").neq("file_id", file_id).execute()
        return f"Found {len(result.data)} other invoices"
    except Exception as e:
        return f"Error fetching invoices: {str(e)}"

@tool
def push_invoice(invoice_data: str) -> str:
    """
    Push valid invoice data into invoice_db.
    
    Args:
        invoice_data: JSON string of the invoice data
    """
    try:
        if isinstance(invoice_data, str):
            data = json.loads(invoice_data)
        else:
            data = invoice_data
            
        supabase.table("invoice_db").insert([data]).execute()
        return "Successfully inserted invoice into invoice_db"
    except Exception as e:
        return f"Error pushing invoice: {str(e)}"

@tool
def send_invalid_email(email_data: str) -> str:
    """
    Send invalidation reason via Gmail SMTP.
    
    Args:
        email_data: JSON string with:
          {
            "recipient_email": "string",
            "reason": "string"
          }
    """
    try:
        # Parse input
        data = json.loads(email_data) if isinstance(email_data, str) else email_data
        recipient = data.get("recipient_email") or data.get("Received_From")
        reason    = data.get("reason", "Invoice validation failed")

        if not recipient:
            return "Error: No recipient email provided."

        # Build the message
        msg = MIMEText(f"Your invoice was rejected for this reason:\n\n{reason}")
        msg["Subject"] = "Invoice Validation Failed"
        msg["From"] = os.getenv("SMTP_USER")
        msg["To"] = recipient

        # Send via SMTP
        with smtplib.SMTP(os.getenv("SMTP_HOST"), int(os.getenv("SMTP_PORT"))) as server:
            server.starttls()
            server.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASS"))
            server.send_message(msg)

        return f"Email sent to {recipient}"

    except Exception as e:
        return f"Error sending email: {e}"

def generate_validation_reason(invoice_data):
    """Generate a validation failure reason based on missing/invalid fields"""
    required_fields = ['Company Name', 'Invoice Number', 'Invoice Date', 'Total Amount', 'GSTIN', 'Customer Name']
    missing_fields = [field for field in required_fields if not invoice_data.get(field) or invoice_data.get(field) == "null"]
    
    issues = []
    if missing_fields:
        issues.append(f"Missing required fields: {', '.join(missing_fields)}")
    
    if invoice_data.get('Total Amount') == 0:
        issues.append("Total Amount is zero")
    
    if not invoice_data.get('Taxes') or invoice_data.get('Taxes') == "null":
        issues.append("Tax information is missing")
    
    return "; ".join(issues) if issues else "Invoice validation failed"