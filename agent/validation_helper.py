import json
from typing import Tuple, Dict, Any

def validate_invoice(invoice_data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate invoice data and return validation result with reason.
    
    Args:
        invoice_data: Dictionary containing invoice information
        
    Returns:
        Tuple of (is_valid: bool, reason: str)
    """
    required_fields = [
        'Company Name',
        'Invoice Number', 
        'Invoice Date',
        'Total Amount',
        'GSTIN',
        'Customer Name'
    ]
    
    missing_fields = []
    validation_issues = []
    
    # Check for missing required fields
    for field in required_fields:
        if not invoice_data.get(field) or invoice_data.get(field) == "null":
            missing_fields.append(field)
    
    # Check for specific validation issues
    if invoice_data.get('Total Amount') == 0 or invoice_data.get('Total Amount') is None:
        validation_issues.append("Total Amount is zero or missing")
    
    if invoice_data.get('GSTIN') and len(str(invoice_data.get('GSTIN'))) != 15:
        validation_issues.append("GSTIN format is invalid (should be 15 characters)")
    
    if not invoice_data.get('Invoice Date'):
        validation_issues.append("Invoice Date is missing")
    
    if not invoice_data.get('Taxes') or invoice_data.get('Taxes') == "null":
        validation_issues.append("Tax information is missing")
    
    # Compile reason
    if missing_fields or validation_issues:
        reason_parts = []
        if missing_fields:
            reason_parts.append(f"Missing required fields: {', '.join(missing_fields)}")
        if validation_issues:
            reason_parts.append(f"Validation issues: {'; '.join(validation_issues)}")
        
        reason = ". ".join(reason_parts)
        return False, reason
    
    return True, "Invoice validation passed"

# Tool wrapper for the validation function
from langchain.tools import tool

@tool
def validate_invoice_tool(invoice_json: str) -> str:
    """
    Validate invoice and return validation result with reason.
    
    Args:
        invoice_json: JSON string of the invoice data
        
    Returns:
        JSON string with validation result and reason
    """
    try:
        if isinstance(invoice_json, str):
            invoice_data = json.loads(invoice_json)
        else:
            invoice_data = invoice_json
            
        is_valid, reason = validate_invoice(invoice_data)
        
        return json.dumps({
            "is_valid": is_valid,
            "reason": reason
        })
        
    except Exception as e:
        return json.dumps({
            "is_valid": False,
            "reason": f"Error during validation: {str(e)}"
        })