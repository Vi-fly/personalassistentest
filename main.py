import os
import json
import sys
import os
import csv
import pandas as pd
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydantic import BaseModel
from phi.llm.groq import Groq
from phi.assistant import Assistant
from dotenv import load_dotenv
from models.request_model import OperationType
from agents.add_agent import process_add_command
from agents.edit_agent import process_edit_command
from agents.delete_agent import process_delete_command
from agents.view_agent import process_view_command

load_dotenv()

# Define a proper Pydantic model for router classification
class RouterClassificationModel(BaseModel):
    operation: str  # Will be one of OperationType values ("0", "1", "2", "3")
    target: str      # "contacts" or "tasks"

# Updated router assistant
router_assistant = Assistant(
    llm=Groq(model="mixtral-8x7b-32768"),
    description="Classify commands into numeric operations and targets",
    instructions=[
        "Analyze the command and output JSON with:",
        "  - operation: one of '0' (add), '1' (edit), '2' (delete), '3' (view)",
        "  - target: 'contacts' or 'tasks'",
        "Example: 'add contact John' → {'operation':'0','target':'contacts'}",
        "Only return valid JSON."
    ],
    output_model=RouterClassificationModel,
    show_tool_calls=True
)

def format_tasks_as_table(tasks):
    """Format task data as a table."""
    df = pd.DataFrame(tasks)
    return df.to_string(index=False)

def master_process_command(raw_command: str) -> dict:
    """Process user command through router to appropriate agent"""
    try:
        # Get classification from router
        classification = router_assistant.run(raw_command).dict()
        
        # Convert operation to OperationType
        op = classification.get("operation", "")
        target = classification.get("target", "").lower()

        # Route to appropriate agent
        response_message = ""
        if op == OperationType.ADD:
            result = process_add_command(raw_command)
            response_message = f"Successfully added to {target}."
        elif op == OperationType.EDIT:
            result = process_edit_command(raw_command)
            response_message = f"Changes have been made to {target}."
        elif op == OperationType.DELETE:
            result = process_delete_command(raw_command)
            response_message = f"The requested {target} entry has been removed."
        elif op == OperationType.VIEW:
            result = process_view_command(raw_command)
            if target == "tasks" and "data" in result:
                response_message = "Here are the tasks assigned to the requested person:\n" + format_tasks_as_table(result["data"])
            else:
                response_message = f"Here is the requested information about {target}."
        else:
            result = {"status": "failed", "message": "I couldn't understand your request. Please try again."}
            response_message = "I'm not sure what you mean. Can you rephrase?"
            
        return {"classification": classification, "result": result, "message": response_message}

    except Exception as e:
        return {
            "classification": {"error": str(e)},
            "result": {"status": "error", "message": "Something went wrong while processing your request."},
            "message": "Oops! Something went wrong. Please try again later."
        }

def initialize_files():
    """Create CSV files with headers if they don't exist"""
    for file, headers in [("contacts.csv", ["Name", "Phone", "Email", "Address"]),
                         ("tasks.csv", ["Title", "Description", "DueDate", "Status", "AssignedTo"])]:
        if not os.path.exists(file):
            with open(file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(headers)

def main():
    initialize_files()
    while True:
        try:
            raw_command = input("\nHow can I assist you today? (Type 'exit' to quit): ").strip()
            if raw_command.lower() == "exit":
                print("Goodbye! Have a great day!")
                break
                
            output = master_process_command(raw_command)
            print("\n🤖 Here's what I found:")
            print(output["message"])
            
        except KeyboardInterrupt:
            print("\nOperation cancelled. See you next time!")
            break

if __name__ == "__main__":
    main()
