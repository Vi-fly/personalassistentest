import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import csv
import json
from typing import Dict, Any, List
from models.request_model import RequestModel, OperationType
from phi.assistant import Assistant
from phi.llm.groq import Groq
from dotenv import load_dotenv
from utils.csv_utils import (
    row_matches,
    CONTACT_HEADERS,
    TASK_HEADERS
)

# Load environment variables
load_dotenv()

def _apply_sorting(data: List[List[str]], headers: List[str], params: Dict) -> None:
    """Helper method for sorting data"""
    sort_field = params["sort_by"].replace(" ", "").lower()
    order = params.get("order", "asc").lower()
    
    header_index = {h.lower().replace(" ", ""): i for i, h in enumerate(headers)}
    
    if sort_field in header_index:
        index = header_index[sort_field]
        reverse_order = order == "desc"
        data.sort(key=lambda x: x[index].lower(), reverse=reverse_order)

def _format_result(data: List[List[str]], headers: List[str]) -> Dict:
    """Format CSV rows into JSON-friendly dicts"""
    if not data:
        return {"status": "failed", "message": "No matching records found"}
    
    return {
        "status": "success",
        "data": [dict(zip(headers, row)) for row in data]
    }

def process_contact_view(request: RequestModel) -> dict:
    """View contacts with filtering and sorting"""
    file_path = "contacts.csv"
    params = request.parameters
    criteria = params.get("criteria", {})

    try:
        # Read contacts
        contacts = []
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                contacts = list(csv.reader(f))
        
        # Filter contacts
        matching = [row for row in contacts if not criteria or row_matches(row, CONTACT_HEADERS, criteria)]
        
        # Apply sorting
        if params.get("sort_by"):
            _apply_sorting(matching, CONTACT_HEADERS, params)
        
        return _format_result(matching, CONTACT_HEADERS)

    except Exception as e:
        return {"status": "error", "message": str(e)}

def process_task_view(request: RequestModel) -> dict:
    """View tasks with filtering and sorting"""
    file_path = "tasks.csv"
    params = request.parameters
    criteria = params.get("criteria", {})

    try:
        # Read tasks
        tasks = []
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                tasks = list(csv.reader(f))
        
        # Filter tasks
        matching = [row for row in tasks if not criteria or row_matches(row, TASK_HEADERS, criteria)]
        
        # Apply sorting
        if params.get("sort_by"):
            _apply_sorting(matching, TASK_HEADERS, params)
        
        return _format_result(matching, TASK_HEADERS)

    except Exception as e:
        return {"status": "error", "message": str(e)}

view_assistant = Assistant(
    llm=Groq(model="mixtral-8x7b-32768"),
    description="Convert view commands to structured format",
    instructions=[
        "Analyze the following user command and extract the filtering criteria. Only include keys that exist in the CSV headers.",
        "For contacts, the valid keys are: Name, Phone, Email, and Address.",
        "For tasks, the valid keys are: Title, Description, DueDate, Status, and AssignedTo.",
        "{",
        '  "operation": "3",',
        '  "target": "<contacts or tasks>",',
        '  "parameters": {',
        '      "criteria": { <only include keys that match the existing fields> }',
        "  }",
        "}",
        "For example, if the input is:",
        "'show task assign to mohit',",
        "the output should be:",
        '{ "operation": "3", "target": "tasks", "parameters": { "criteria": { "AssignedTo": "mohit" } } }',
        "Only return valid JSON"
    ],
    output_model=RequestModel,
    show_tool_calls=True
)

def process_view_command(raw_command: str) -> Dict[str, Any]:
    """Main entry point for view operations"""
    try:
        structured = view_assistant.run(raw_command)
        request_data = structured.dict() if hasattr(structured, "dict") else json.loads(structured)
        
        request = RequestModel(**request_data)
        if request.target.lower() == "contacts":
            return process_contact_view(request)
        elif request.target.lower() == "tasks":
            return process_task_view(request)
        return {"status": "failed", "message": "Invalid target"}
    
    except Exception as e:
        return {"status": "error", "message": f"View failed: {str(e)}"}

if __name__ == "__main__":
    # For testing only - use with python -m agents.view_agent
    while True:
        command = input("Enter view command (or 'exit'): ")
        if command.lower() == "exit":
            break
        result = process_view_command(command)
        print(json.dumps(result, indent=2))