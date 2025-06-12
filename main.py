import sys
import os
import json

# Ensure the parent folder is on the path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from langchain.agents import initialize_agent, AgentType
from langchain.agents import Tool
from langchain_community.llms import Ollama
from ocr.ocr_main import process_latest_invoice
from agent import tools as t
from agent.prompt_loader import load_prompt
from agent.validation_helper import validate_invoice

# Initialize the language model
llm = Ollama(model="mistral")

# Define available tools
tools = [
    Tool.from_function(
        func=t.update_flagged,
        name='update_flagged',
        description=(
            "Update the flagged status of a document. "
            "Pass a JSON string with file_id and is_valid fields. "
            "Use is_valid=true for valid invoices, is_valid=false for invalid invoices."
        )
    ),
    Tool.from_function(
        func=t.fetch_other_invoices,
        name='fetch_other_invoices',
        description='Fetch all invoice records except the current one. Pass the current file_id as parameter.'
    ),
    Tool.from_function(
        func=t.push_invoice,
        name='push_invoice',
        description='Push valid invoices to invoice_db table. Pass the invoice data as JSON string.'
    ),
    Tool.from_function(
        func=t.send_invalid_email,
        name='send_invalid_email',
        description=(
            "Send emails for invalid invoices. "
            "Pass a JSON string with recipient_email and reason fields."
        )
    )
]

# Initialize the agent executor with parsing error handling enabled
agent_executor = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    handle_parsing_errors=True  # Retry on parsing errors
)


def main():
    # Load the updated system prompt
    system_prompt = load_prompt('prompt/agent_prompt.md')
    invoice, file_id = process_latest_invoice()
    if not invoice:
        print("No invoice to process.")
        return

    try:
        invoice_dict = json.loads(invoice) if isinstance(invoice, str) else invoice
        is_valid, validation_reason = validate_invoice(invoice_dict)
        print(f"Validation Result: {'VALID' if is_valid else 'INVALID'}")
        print(f"Validation Reason: {validation_reason}")
    except Exception as e:
        is_valid = False
        validation_reason = f"Error during validation: {str(e)}"
        print(f"Validation Error: {validation_reason}")

    recipient_email = invoice_dict.get('Received_From', 'unknown')

    # Construct agent input using strict Action/Action Input format
    if is_valid:
        agent_input = f"""
{system_prompt}

Thought: Invoice is valid. Updating flagged status.
Action: update_flagged
Action Input: {{"file_id": "{file_id}", "is_valid": true}}

Thought: Flag updated. Pushing invoice to database.
Action: push_invoice
Action Input: {json.dumps(invoice_dict)}
"""
    else:
        agent_input = f"""
{system_prompt}

Thought: Invoice is invalid. Updating flagged status.
Action: update_flagged
Action Input: {{"file_id": "{file_id}", "is_valid": false}}

Thought: Flag updated. Sending invalid email.
Action: send_invalid_email
Action Input: {{"recipient_email": "{recipient_email}", "reason": "{validation_reason}"}}
"""

    try:
        result = agent_executor.invoke({"input": agent_input})
        print("Agent execution completed successfully")
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error during agent execution: {e}")


if __name__ == "__main__":
    main()