import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import csv
import json
from typing import Dict, Any
from models.request_model import RequestModel, OperationType
from phi.assistant import Assistant
from phi.llm.groq import Groq
from dotenv import load_dotenv
from utils.csv_utils import (
    row_matches,
    parse_relative_date,
    CONTACT_HEADERS,
    TASK_HEADERS
)

# Load environment variables
load_dotenv()

def update_csv_row(row: list, headers: list, updates: Dict[str, Any]) -> list:
    """Apply updates to a CSV row based on headers"""
    return [str(updates.get(header, val)).strip() for header, val in zip(headers, row)]

def contact_exists(name: str) -> bool:
    """Check if a contact exists in contacts.csv"""
    if not os.path.exists("contacts.csv"):
        return False
        
    with open("contacts.csv", "r") as f:
        reader = csv.reader(f)
        for row in reader:
            if row and row[0].strip().lower() == name.lower():
                return True
    return False

def process_contact_edit(request: RequestModel) -> Dict[str, Any]:
    """Edit contacts in contacts.csv matching criteria"""
    file_path = "contacts.csv"
    params = request.parameters
    criteria = params.get("criteria", {})
    updates = params.get("updates", {})

    if not criteria or not updates:
        return {"status": "failed", "message": "Missing criteria or updates"}

    try:
        # Read and process contacts
        updated_count = 0
        contacts = []
        
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                contacts = list(csv.reader(f))

        new_contacts = []
        for row in contacts:
            if row_matches(row, CONTACT_HEADERS, criteria):
                new_row = update_csv_row(row, CONTACT_HEADERS, updates)
                new_contacts.append(new_row)
                updated_count += 1
            else:
                new_contacts.append(row)

        if updated_count == 0:
            return {"status": "failed", "message": "No matching contacts found"}

        # Write updated data
        with open(file_path, "w", newline="") as f:
            csv.writer(f).writerows(new_contacts)
            
        return {"status": "success", "message": f"Updated {updated_count} contacts"}

    except Exception as e:
        return {"status": "error", "message": str(e)}

def process_task_edit(request: RequestModel) -> Dict[str, Any]:
    """Edit tasks with proper CSV validation"""
    file_path = "tasks.csv"
    params = request.parameters
    criteria = params.get("criteria", {})
    updates = params.get("updates", {})

    if not criteria or not updates:
        return {"status": "failed", "message": "Missing criteria or updates"}

    try:
        # Read tasks with proper CSV validation
        tasks = []
        with open(file_path, "r") as f:
            reader = csv.reader(f)
            try:
                headers = next(reader)  # Skip header
            except StopIteration:
                headers = []
            for row in reader:
                # Clean malformed rows
                cleaned_row = [col.strip() for col in row[:5]]  # Only keep first 5 columns
                if len(cleaned_row) < 5:
                    cleaned_row += [''] * (5 - len(cleaned_row))
                tasks.append(cleaned_row)

        # Process updates
        updated_count = 0
        new_tasks = []
        for row in tasks:
            if row_matches(row, TASK_HEADERS, criteria):
                # Apply updates only to relevant columns
                updated_row = [
                    updates.get("Title", row[0]),
                    updates.get("Description", row[1]),
                    updates.get("Due Date", row[2]),
                    updates.get("Status", row[3]),
                    updates.get("Assigned To", row[4])
                ]
                new_tasks.append(updated_row)
                updated_count += 1
            else:
                new_tasks.append(row)

        # Write back with proper CSV format
        with open(file_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(TASK_HEADERS)
            writer.writerows(new_tasks)

        return {"status": "success", "message": f"Updated {updated_count} tasks"}

    except Exception as e:
        return {"status": "error", "message": str(e)}

edit_assistant = Assistant(
    llm=Groq(model="mixtral-8x7b-32768"),
    description="Convert edit commands to structured format",
    instructions=[
        "Convert user command to JSON with:",
        "- operation: '1' (edit)",
        "- target: 'tasks'",
        "- parameters: {criteria: {Title: 'TASK_TITLE'}, updates: {Status: 'NEW_STATUS'}}",
        "Example 1: 'mark task 'looting' as completed' →",
        "{'operation':'1','target':'tasks','parameters':{",
        "  'criteria':{'Title':'looting'}, 'updates':{'Status':'Completed'}}}",
        "Example 2: 'update status of 'Follow Up' to pending' →",
        "{'operation':'1','target':'tasks','parameters':{",
        "  'criteria':{'Title':'Follow Up'}, 'updates':{'Status':'Pending'}}}",
        "Always include explicit Title criteria for task updates",
    ],
    output_model=RequestModel,
    show_tool_calls=True
)

def process_edit_command(raw_command: str) -> Dict[str, Any]:
    """Main entry point for edit operations"""
    try:
        # Get structured request from LLM
        structured = edit_assistant.run(raw_command)
        request_data = structured.dict() if hasattr(structured, "dict") else json.loads(structured)

        # Validate and process request
        request = RequestModel(**request_data)
        if request.target.lower() == "contacts":
            return process_contact_edit(request)
        elif request.target.lower() == "tasks":
            return process_task_edit(request)
        return {"status": "failed", "message": "Invalid target"}
        
    except Exception as e:
        return {"status": "error", "message": f"Edit failed: {str(e)}"}

if __name__ == "__main__":
    # For testing only - use with python -m agents.edit_agent
    while True:
        command = input("Enter edit command (or 'exit'): ")
        if command.lower() == "exit":
            break
        result = process_edit_command(command)
        print(json.dumps(result, indent=2))
        
import re

def fallback_parse_edit_command(raw_command: str) -> Dict[str, Dict[str, Any]]:
    """Improved fallback parser for status updates"""
    lower_cmd = raw_command.lower()
    updates = {}
    criteria = {}

    # Pattern: "mark task 'TITLE' as STATUS"
    mark_pattern = r"mark\s+task\s+['\"](.*?)['\"]\s+as\s+(\w+)"
    mark_match = re.search(mark_pattern, raw_command, re.IGNORECASE)
    if mark_match:
        criteria["Title"] = mark_match.group(1).strip()
        updates["Status"] = mark_match.group(2).strip()
        return {"criteria": criteria, "updates": updates}

    # Pattern: "update status of 'TITLE' to STATUS"
    update_pattern = r"update\s+status\s+of\s+['\"](.*?)['\"]\s+to\s+(\w+)"
    update_match = re.search(update_pattern, raw_command, re.IGNORECASE)
    if update_match:
        criteria["Title"] = update_match.group(1).strip()
        updates["Status"] = update_match.group(2).strip()
        return {"criteria": criteria, "updates": updates}

    # Existing parsing logic...
    return {"criteria": criteria, "updates": updates}