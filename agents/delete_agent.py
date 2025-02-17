
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import os
import csv
import json
from typing import Dict, Any
from models.request_model import RequestModel
from utils.csv_utils import CONTACT_HEADERS, TASK_HEADERS, row_matches
from phi.assistant import Assistant
from phi.llm.groq import Groq
from dotenv import load_dotenv

load_dotenv()

def process_contact_delete(request: RequestModel) -> dict:
    """Delete contacts from contacts.csv matching criteria."""
    file_path = "contacts.csv"
    criteria = request.parameters.get("criteria", {})
    
    if not criteria:
        return {"status": "failed", "message": "No deletion criteria provided."}

    try:
        # Read existing contacts
        contacts = []
        if os.path.exists(file_path):
            with open(file_path, "r", newline="") as f:
                reader = csv.reader(f)
                contacts = list(reader)

        # Filter out rows matching the criteria
        new_contacts = [
            row for row in contacts 
            if not row_matches(row, CONTACT_HEADERS, criteria)
        ]

        if len(new_contacts) == len(contacts):
            return {"status": "failed", "message": "No matching contacts found."}

        # Write updated data back to file
        with open(file_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(new_contacts)
            
        return {"status": "success", "message": f"Deleted {len(contacts)-len(new_contacts)} contact(s)."}
    
    except Exception as e:
        return {"status": "error", "message": str(e)}

def process_task_delete(request: RequestModel) -> dict:
    """Delete tasks from tasks.csv matching criteria."""
    file_path = "tasks.csv"
    criteria = request.parameters.get("criteria", {})
    
    if not criteria:
        return {"status": "failed", "message": "No deletion criteria provided."}

    try:
        # Read existing tasks
        tasks = []
        if os.path.exists(file_path):
            with open(file_path, "r", newline="") as f:
                reader = csv.reader(f)
                tasks = list(reader)

        # Filter out rows matching the criteria
        new_tasks = [
            row for row in tasks 
            if not row_matches(row, TASK_HEADERS, criteria)
        ]

        if len(new_tasks) == len(tasks):
            return {"status": "failed", "message": "No matching tasks found."}

        # Write updated data back to file
        with open(file_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(new_tasks)
            
        return {"status": "success", "message": f"Deleted {len(tasks)-len(new_tasks)} task(s)."}
    
    except Exception as e:
        return {"status": "error", "message": str(e)}

def fallback_parse_delete_command(raw_command: str, target: str) -> Dict[str, Dict[str, Any]]:
    """
    Fallback parser for delete commands.
    Attempts to extract a field and value from the raw command.
    
    For tasks: if the field is 'task', 'name', or 'tittle', it is normalized to 'Title'.
    For contacts: if no field is provided, it defaults to 'Name'.
    
    Examples:
      "delete task 'addtask'" becomes {"criteria": {"Title": "addtask"}}
      "delete contact 'rachit'" becomes {"criteria": {"Name": "rachit"}}
    """
    criteria = {}
    lower_cmd = raw_command.lower()
    if " where " in lower_cmd:
        parts = raw_command.split(" where ", 1)
        criteria_part = parts[1]
        if " is " in criteria_part.lower():
            crit_parts = criteria_part.split(" is ", 1)
            crit_field = crit_parts[0].strip().replace(" ", "")
            crit_value = crit_parts[1].strip().strip("'\"")
            if target == "contacts" and crit_field.lower() in ["mail", "email"]:
                crit_field = "Email"
            elif target == "tasks" and crit_field.lower() in ["task", "name", "tittle"]:
                crit_field = "Title"
            criteria[crit_field.capitalize()] = crit_value
    else:
        tokens = raw_command.split()
        if target == "tasks" and len(tokens) == 3:
            value = tokens[2].strip().strip("'\"")
            criteria["Title"] = value
        elif target == "contacts" and len(tokens) == 3:
            value = tokens[2].strip().strip("'\"")
            criteria["Name"] = value  # Default for contacts is now Name
    return {"criteria": criteria} if criteria else {}

def process_delete_parameters(request_data: dict, raw_input: str) -> dict:
    """
    Ensures that the 'parameters' dict in request_data includes a 'criteria' dict.
    If not, uses the fallback parser with the target from request_data.
    """
    parameters = request_data.get("parameters", {})
    if "criteria" not in parameters or not parameters["criteria"]:
        target = request_data.get("target", "").lower()
        fallback = fallback_parse_delete_command(raw_input, target)
        if fallback:
            request_data["parameters"] = fallback
    return request_data

def execute_operation(request_data: dict) -> dict:
    try:
        from models.request_model import RequestModel  # Re-import if necessary
        request = RequestModel(**request_data)
        target = request.target.lower()
        if target == "contacts":
            return process_contact_delete(request)
        elif target == "tasks":
            return process_task_delete(request)
        else:
            return {"status": "failed", "message": "Invalid target. Choose 'contacts' or 'tasks'."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

delete_assistant = Assistant(
    llm=Groq(model="mixtral-8x7b-32768"),
    description="Convert natural language delete commands into JSON for deleting contacts or tasks.",
    instructions=[
        "Convert the request into JSON with fields:",
        "  - operation: set to '2' for delete",
        "  - target: either 'contacts' or 'tasks'",
        "  - parameters: include a 'criteria' dictionary to identify records to delete.",
        "Example: 'delete contact where email is test@test.com' should produce:",
        "{ 'operation': '2', 'target': 'contacts', 'parameters': { 'criteria': {'Email': 'test@test.com'} } }",
        "If the JSON output does not include 'criteria', use a fallback parser that extracts the field and value.",
        "Only return valid JSON."
    ],
    output_model=RequestModel,
    show_tool_calls=True
)

def process_delete_command(raw_command: str) -> dict:
    """Main entry point for delete operations."""
    try:
        structured = delete_assistant.run(raw_command)
        if isinstance(structured, str):
            request_data = json.loads(structured)
        else:
            request_data = structured.dict()
        request_data = process_delete_parameters(request_data, raw_command)
        request = RequestModel(**request_data)
        if request.target.lower() == "contacts":
            return process_contact_delete(request)
        elif request.target.lower() == "tasks":
            return process_task_delete(request)
        else:
            return {"status": "failed", "message": "Invalid target."}
    except Exception as e:
        return {"status": "error", "message": f"Delete failed: {str(e)}"}

def delete_main():
    while True:
        raw_input_text = input("Enter command to delete a contact or a task (or 'exit' to quit): ")
        if raw_input_text.lower() == "exit":
            break
        result = process_delete_command(raw_input_text)
        print("Result:", json.dumps(result, indent=2))

if __name__ == "__main__":
    delete_main()
