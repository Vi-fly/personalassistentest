# models/request_model.py
from typing import Dict, Any
from enum import Enum
from pydantic import BaseModel

class OperationType(str, Enum):
    """Numeric codes for operations (matches your add_agent.py setup)"""
    ADD = "0"
    EDIT = "1"
    DELETE = "2"
    VIEW = "3"

class RequestModel(BaseModel):
    """Request structure for agent operations"""
    operation: OperationType  # Numeric code from OperationType
    target: str  # "contacts" or "tasks"
    parameters: Dict[str, Any]