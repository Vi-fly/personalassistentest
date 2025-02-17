import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import os
import csv
import json
from typing import Dict, Any
from enum import Enum
from datetime import datetime
import parsedatetime as pdt  # For relative date parsing
from pydantic import BaseModel
from phi.assistant import Assistant
from phi.llm.groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class OperationType(str, Enum):
    ADD = "0"
    # Additional operations can be defined later

class RequestModel(BaseModel):
    operation: OperationType
    parameters: Dict[str, Any]
    target: str  # "contacts" or "tasks"

def process_contact_add(request: RequestModel) -> dict:
    """Process the add operation on contacts.csv with validation.
       If 'Address' is not provided, an empty field is written.
    """
    file_path = "contacts.csv"
    
    name = str(request.parameters.get("Name", "")).strip()
    phone = str(request.parameters.get("Phone", "")).strip()
    email = str(request.parameters.get("Email", "")).strip()
    # Ensure address is an empty string if not provided.
    address = str(request.parameters.get("Address", "")).strip() if request.parameters.get("Address") else ""
    
    if not name or not phone or not email:
        return {"status": "failed", "message": "Name, Phone and Email are required"}
    
    # Read existing contacts
    existing_contacts = []
    if os.path.exists(file_path):
        with open(file_path, mode='r', newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 3:
                    existing_contacts.append(row)
    
    for row in existing_contacts:
        if phone == row[1]:
            return {"status": "failed", "message": "Phone number exists"}
        if email.lower() == row[2].lower():
            return {"status": "failed", "message": "Email exists"}
    
    try:
        with open(file_path, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([name, phone, email, address])
        return {"status": "success", "message": "Contact added"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def parse_relative_date(date_str: str) -> str:
    """
    Uses parsedatetime's parseDT to convert a relative date string into YYYY-MM-DD format.
    Pre-filters common keywords.
    """
    lower_str = date_str.lower()
    if "tomorrow" in lower_str:
        date_str = "tomorrow"
    elif "next week" in lower_str:
        date_str = "next week"
    elif "next month" in lower_str:
        date_str = "next month"
    
    cal = pdt.Calendar()
    dt, parse_status = cal.parseDT(date_str, sourceTime=datetime.now())
    if parse_status:
        return dt.strftime("%Y-%m-%d")
    else:
        return date_str  # Fallback if parsing fails

def process_task_add(request: RequestModel) -> dict:
    """
    Process the add operation on tasks.csv.
    Expected CSV columns: Title, Description, DueDate, Status, AssignedTo.
      - Title is required.
      - Status defaults to 'on going'.
      - AssignedTo defaults to 'None'.
      - DueDate may be relative (e.g., 'tomorrow'); convert it.
      - If AssignedTo is provided and not 'None', it must exist in contacts.csv.
    """
    file_path = "tasks.csv"
    
    title = str(request.parameters.get("Title", "")).strip()
    description = str(request.parameters.get("Description", "")).strip() if request.parameters.get("Description") else ""
    due_date_input = str(request.parameters.get("DueDate", "")).strip() if request.parameters.get("DueDate") else ""
    status = str(request.parameters.get("Status", "on going")).strip()
    assigned_to = str(request.parameters.get("AssignedTo", "None")).strip()
    
    if not title:
        return {"status": "failed", "message": "Task Title is required"}
    
    if due_date_input:
        due_date = parse_relative_date(due_date_input)
    else:
        due_date = ""
    
    # Check uniqueness: Title must not already exist (case-insensitive)
    existing_tasks = []
    if os.path.exists(file_path):
        with open(file_path, "r", newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 1:
                    existing_tasks.append(row)
    for row in existing_tasks:
        if title.lower() == row[0].lower():
            return {"status": "failed", "message": "Task title exists"}
    
    # Validate assigned contact
    if assigned_to.lower() != "none" and assigned_to != "":
        contacts_file = "contacts.csv"
        contact_found = False
        if os.path.exists(contacts_file):
            with open(contacts_file, "r", newline="") as f:
                reader = csv.reader(f)
                for row in reader:
                    if row and row[0].strip().lower() == assigned_to.lower():
                        contact_found = True
                        break
        if not contact_found:
            return {"status": "failed", "message": f"Assigned contact '{assigned_to}' not found"}
    
    try:
        with open(file_path, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([title, description, due_date, status, assigned_to])
        return {"status": "success", "message": "Task added"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def process_add_command(raw_command: str) -> dict:
    """
    Uses an Assistant to convert a raw add command into structured JSON and then
    dispatches the command to the appropriate add function.
    Includes fallback parsing for comma-separated input for contacts.
    """
    add_assistant = Assistant(
        llm=Groq(model="mixtral-8x7b-32768"),
        description="Convert natural language add commands into JSON for adding a contact or a task.",
        instructions=[
            "Convert the request into JSON with fields: operation (set to '0' for add), target ('contacts' or 'tasks'), and parameters.",
            "For contacts, include: Name, Phone, Email, and optionally Address.",
            "For tasks, include: Title (required), and optionally Description, DueDate, Status, and AssignedTo.",
            "Only return valid JSON."
        ],
        output_model=RequestModel,
        show_tool_calls=True
    )
    structured = add_assistant.run(raw_command)
    if isinstance(structured, str):
        request_data = json.loads(structured)
    else:
        request_data = structured.dict()
    request = RequestModel(**request_data)
    
    # Fallback parsing for contacts if required fields are missing
    if request.target.lower() == "contacts":
        if not (request.parameters.get("Name") and request.parameters.get("Phone") and request.parameters.get("Email")):
            lower_cmd = raw_command.lower()
            if lower_cmd.startswith("add contact"):
                content = raw_command[len("add contact"):].strip()
                parts = [p.strip() for p in content.split(",") if p.strip()]
                if len(parts) >= 3:
                    request.parameters["Name"] = parts[0]
                    request.parameters["Phone"] = parts[1]
                    request.parameters["Email"] = parts[2]
                    # Optionally, if there's a fourth part, set Address
                    if len(parts) >= 4:
                        request.parameters["Address"] = parts[3]
    
    if request.target.lower() == "contacts":
        return process_contact_add(request)
    elif request.target.lower() == "tasks":
        return process_task_add(request)
    else:
        return {"status": "failed", "message": "Invalid target."}

def add_main():
    while True:
        raw_input_text = input("Enter command to add a contact or a task (or 'exit' to quit): ")
        if raw_input_text.lower() == "exit":
            break
        result = process_add_command(raw_input_text)
        print("Result:", json.dumps(result, indent=2))

if __name__ == "__main__":
    # Ensure CSV files exist; if not, create them
    for file in ["contacts.csv", "tasks.csv"]:
        if not os.path.exists(file):
            with open(file, "w") as f:
                pass
    add_main()
