from typing import Dict, Tuple
import re


def get_lesson_range_for_module(weeks_data: Dict, module_number: int) -> str:
    """
    Calculate the lesson range for a given module by analyzing the original Excel data
    to find where module numbers change.
    
    Args:
        weeks_data: Dictionary containing all weeks data
        module_number: The module number to calculate range for
        
    Returns:
        String representing the lesson range (e.g., "1A-1D")
    """
    # We need to re-read the Excel file to get the raw row-by-row data
    # and detect module transitions
    try:
        import pandas as pd
        import numpy as np
        
        # Re-read the Excel file (assuming it's in the standard location)
        excel_path = "files/yaml/schedule.xlsx"
        df = pd.read_excel(excel_path, engine="openpyxl")
        df = df.replace(np.nan, "")
        
        # Find lesson ranges by detecting module transitions
        module_ranges = {}
        current_module = None
        start_lesson = None
        

        
        for index, row in df.iterrows():
            if index == 0:  # Skip header row
                continue
                
            # Column C contains module info (index 2)
            module_cell = str(row.iloc[2]).strip()
            lesson_cell = str(row.iloc[3]).strip()
            
            # Extract module number from module cell
            extracted_module = None
            if module_cell:
                import re
                # Look for patterns like "Module 1", "Mod. 2", "Mod 3", etc.
                match = re.search(r'(?:Module?\.?\s*)?(\d+)', module_cell, re.IGNORECASE)
                if match:
                    extracted_module = int(match.group(1))
            
            # If we found a valid lesson and it's not a placeholder
            if lesson_cell and lesson_cell != "-":
                
                # If this is the start or we detected a module change
                if current_module is None or (extracted_module and extracted_module != current_module):
                    
                    # If we had a previous module, finalize its range
                    if current_module is not None and start_lesson:
                        # The previous row had the end lesson for the previous module
                        prev_index = index - 1
                        if prev_index > 0:
                            prev_lesson = str(df.iloc[prev_index, 3]).strip()
                            if prev_lesson and prev_lesson != "-":
                                end_lesson = prev_lesson
                            else:
                                # Find the last valid lesson before this
                                end_lesson = start_lesson
                                for back_idx in range(prev_index, 0, -1):
                                    back_lesson = str(df.iloc[back_idx, 3]).strip()
                                    if back_lesson and back_lesson != "-":
                                        end_lesson = back_lesson
                                        break
                        else:
                            end_lesson = start_lesson
                            
                        if start_lesson == end_lesson:
                            module_ranges[current_module] = start_lesson
                        else:
                            module_ranges[current_module] = f"{start_lesson}-{end_lesson}"
                    
                    # Start tracking the new module
                    if extracted_module:
                        current_module = extracted_module
                        start_lesson = lesson_cell
                
                # If we're in a module but no module transition, just continue
                # (we'll use the lesson as potential end lesson)
        
        # Handle the last module
        if current_module is not None and start_lesson:
            # Find the last lesson in the dataset
            end_lesson = start_lesson
            for back_idx in range(len(df) - 1, 0, -1):
                back_lesson = str(df.iloc[back_idx, 3]).strip()
                if back_lesson and back_lesson != "-":
                    end_lesson = back_lesson
                    break
                    
            if start_lesson == end_lesson:
                module_ranges[current_module] = start_lesson
            else:
                module_ranges[current_module] = f"{start_lesson}-{end_lesson}"
        
        # Return the range for the requested module
        if module_number in module_ranges:
            return module_ranges[module_number]
        else:
            return f"{module_number}A-{module_number}D"  # Fallback
            
    except Exception as e:
        print(f"Warning: Could not calculate lesson range for module {module_number}: {e}")
        return f"{module_number}A-{module_number}D"  # Fallback


def get_homework_range_for_module(weeks_data: Dict, module_number: int) -> str:
    """
    Calculate the homework range for a given module (e.g., "Homeworks 1 & 2").
    
    Args:
        weeks_data: Dictionary containing all weeks data
        module_number: The module number to calculate range for
        
    Returns:
        String representing the homework range (e.g., "Homeworks 1 & 2")
    """
    homework_numbers = []
    
    for week_num, week_data in weeks_data.items():
        if week_data.get("module") == module_number:
            # Check each day for homework assignments
            for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
                if day in week_data:
                    assigned = week_data[day].get("assigned", "")
                    due = week_data[day].get("due", "")
                    
                    # Check assigned homework
                    if assigned and "HW" in str(assigned).upper():
                        hw_match = re.search(r'HW\s*(\d+)', str(assigned), re.IGNORECASE)
                        if hw_match:
                            homework_numbers.append(int(hw_match.group(1)))
                    
                    # Check due homework
                    if due and "HW" in str(due).upper():
                        hw_match = re.search(r'HW\s*(\d+)', str(due), re.IGNORECASE)
                        if hw_match:
                            homework_numbers.append(int(hw_match.group(1)))
    
    if not homework_numbers:
        return f"HW{module_number:02d}"  # Default fallback
    
    # Remove duplicates and sort
    homework_numbers = sorted(list(set(homework_numbers)))
    
    if len(homework_numbers) == 1:
        return f"HW{homework_numbers[0]:02d}"
    elif len(homework_numbers) == 2:
        return f"HW{homework_numbers[0]:02d} & HW{homework_numbers[1]:02d}"
    else:
        # For more than 2, use range format
        return f"HW{homework_numbers[0]:02d}-HW{homework_numbers[-1]:02d}"


def format_quiz_date_time(quiz_date: str) -> Tuple[str, str]:
    """
    Format quiz date and time for the template.
    
    Args:
        quiz_date: Date string in MM/DD/YYYY format
        
    Returns:
        Tuple of (formatted_date_time, day_of_week)
    """
    from datetime import datetime
    
    try:
        # Parse the date
        date_obj = datetime.strptime(quiz_date, "%m/%d/%Y")
        
        # Format as "Wednesday, January 29th"
        day_name = date_obj.strftime("%A")
        month_name = date_obj.strftime("%B")
        day = date_obj.day
        
        # Add ordinal suffix
        if 10 <= day % 100 <= 20:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        
        formatted_date = f"{day_name}, {month_name} {day}{suffix}"
        
        return formatted_date, day_name.lower()
        
    except ValueError:
        # If parsing fails, return the original date
        return quiz_date, "wednesday" 