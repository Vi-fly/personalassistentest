"""
Utility functions for CSV operations and date parsing
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import parsedatetime as pdt

# CSV column headers for different entity types
CONTACT_HEADERS = ["Name", "Phone", "Email", "Address"]
TASK_HEADERS = ["Title", "Description", "DueDate", "Status", "AssignedTo"]

def parse_relative_date(date_str: str) -> str:
    """
    Convert relative date expressions to YYYY-MM-DD format.
    Handles common phrases like 'tomorrow', 'next week', and exact dates.
    
    Args:
        date_str (str): Input date string (e.g., "tomorrow", "March 5th")
        
    Returns:
        str: Formatted date string or original input if parsing fails
    """
    cal = pdt.Calendar()
    date_str = date_str.lower().strip()
    
    # Map common phrases to parseable formats
    phrase_mapping = {
        "tomorrow": "tomorrow",
        "next week": "next week",
        "next month": "next month",
        "today": "today",
        "yesterday": "yesterday"
    }
    
    for phrase in phrase_mapping:
        if phrase in date_str:
            date_str = phrase_mapping[phrase]
            break

    dt, parse_status = cal.parseDT(date_str, sourceTime=datetime.now())
    return dt.strftime("%Y-%m-%d") if parse_status else date_str

def row_matches(row: List[str], headers: List[str], criteria: Dict[str, Any]) -> bool:
    """
    Check if a CSV row matches all specified criteria (case-insensitive).
    
    Args:
        row: CSV row data
        headers: List of column headers
        criteria: Dictionary of {field: value} to match
        
    Returns:
        bool: True if all criteria match, False otherwise
    """
    header_index = {h.lower().replace(" ", ""): i for i, h in enumerate(headers)}
    
    for field, target_value in criteria.items():
        norm_field = field.lower().replace(" ", "")
        
        if norm_field not in header_index:
            return False
            
        col_index = header_index[norm_field]
        
        try:
            row_value = str(row[col_index]).strip().lower()
            target_value = str(target_value).strip().lower()
            
            if row_value != target_value:
                return False
        except (IndexError, TypeError):
            return False
            
    return True