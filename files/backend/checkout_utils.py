import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime


def extract_checkout_number(topic: str) -> Optional[str]:
    """
    Extract checkout number from topic text like 'CHECKOUT 1', 'Checkout 2', etc.
    
    Args:
        topic: Topic string to search for checkout pattern
        
    Returns:
        Checkout number as string or None if not found
    """
    if not topic:
        return None
    
    # Look for patterns like "CHECKOUT 1", "Checkout 2", etc.
    patterns = [
        r"CHECKOUT\s*(\d+)",
        r"Checkout\s*(\d+)",
        r"checkout\s*(\d+)"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, topic, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return None


def collect_checkout_assignments(weeks_data: Dict) -> List[Dict]:
    """
    Collect all checkout assignments from the weeks data structure.
    Uses simple mapping: Checkout N = Module N.
    
    Args:
        weeks_data: Dictionary containing all weeks data
        
    Returns:
        List of checkout dictionaries with checkout_number, date, week_number, module
    """
    checkouts = []
    
    for week_num, week_data in weeks_data.items():
        # Skip non-numeric keys like 'icon_urls'
        if not str(week_num).isdigit():
            continue
            
        # Check each day of the week for checkout topics
        for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
            if day in week_data:
                day_data = week_data[day]
                topic = day_data.get("topic", "")
                
                checkout_number = extract_checkout_number(topic)
                if checkout_number:
                    # Simple mapping: Checkout N = Module N
                    module_number = int(checkout_number)
                    checkouts.append({
                        "checkout_number": int(checkout_number),
                        "date": day_data.get("date", ""),
                        "week_number": week_num,
                        "day": day,
                        "module": module_number,
                    })
    
    # Sort by checkout number to ensure proper ordering
    checkouts.sort(key=lambda x: x["checkout_number"])
    return checkouts


def find_homework_due_for_checkout(weeks_data: Dict, checkout_week_num: int) -> Tuple[Optional[str], Optional[str]]:
    """
    Find the homework that is due in the same week as the checkout.
    
    Args:
        weeks_data: Dictionary containing all weeks data
        checkout_week_num: Week number where the checkout occurs
        
    Returns:
        Tuple of (homework_number, homework_due_date) or (None, None) if not found
    """
    if checkout_week_num not in weeks_data:
        return None, None
    
    week_data = weeks_data[checkout_week_num]
    
    # Check each day of the checkout week for homework due
    for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
        if day in week_data:
            day_data = week_data[day]
            due_text = day_data.get("due", "")
            
            if due_text and "HW" in str(due_text).upper():
                # Extract homework number
                hw_match = re.search(r'HW\s*(\d+)', str(due_text), re.IGNORECASE)
                if hw_match:
                    hw_number = hw_match.group(1)
                    due_date = day_data.get("date", "")
                    return hw_number, due_date
    
    return None, None


def get_collaboration_learning_objectives() -> List[str]:
    """
    Get the standard collaboration learning objectives for all checkouts.
    
    Returns:
        List of collaboration learning objectives
    """
    return [
        "LO1: Elicit, listen to, and incorporate ideas from teammates with different perspectives and backgrounds",
        "LO2: Work productively in your teams and with your whole class to learn and solve problems, including asking questions and sharing ideas respectfully, listening to understand, supporting classmates, and valuing the perspectives and experiences of others."
    ]


def get_communications_learning_objectives() -> List[str]:
    """
    Get the standard communications learning objectives for all checkouts.
    
    Returns:
        List of communications learning objectives
    """
    return [
        "LO1: Use a variety of modes to communicate in mechanical engineering. (e.g. oral, written, visual)",
        "LO2: Translate concepts of functions between four points of view (i.e., the \"Rule of Four\"): geometric (graphs), numeric (tables), symbolic (formulas), and verbal (words), with a particular emphasis on translating between words and other representations."
    ]


def format_checkout_due_date(checkout_date: str) -> str:
    """
    Format checkout date for the due date section.
    
    Args:
        checkout_date: Date string in MM/DD/YYYY format
        
    Returns:
        Formatted date string like "Friday, 1/24/2025"
    """
    try:
        # Parse the date
        date_obj = datetime.strptime(checkout_date, "%m/%d/%Y")
        
        # Format as "Friday, 1/24/2025"
        day_name = date_obj.strftime("%A")
        month = date_obj.month
        day = date_obj.day
        year = date_obj.year
        
        return f"{day_name}, {month}/{day}/{year}"
        
    except ValueError:
        # If parsing fails, return the original date
        return checkout_date


def generate_checkout_task_text(homework_number: str, checkout_number: str, homework_url: str = None) -> str:
    """
    Generate the task section text for the checkout with homework reference and link.
    
    Args:
        homework_number: The homework number (e.g., "2")
        checkout_number: The checkout number (e.g., "1")
        homework_url: URL to the homework assignment (optional)
        
    Returns:
        Formatted task text with homework reference and link
    """
    if homework_number:
        if homework_url:
            # Create a clickable link to the homework assignment
            homework_ref = f'<a href="{homework_url}" target="_blank" rel="noopener">Homework {homework_number}, Problem XXX</a>'
        else:
            # Fallback to plain text if no URL available
            homework_ref = f"Homework {homework_number}, Problem XXX"
        return f"Your checkout group is tasked with demonstrating and explaining your solution to this module's checkout problem ({homework_ref}) using the whiteboard as your primary medium to show your approach."
    else:
        return f"Your checkout group is tasked with demonstrating and explaining your solution to this module's checkout problem using the whiteboard as your primary medium to show your approach." 