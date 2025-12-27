from typing import Dict, Tuple, Optional
import re
import requests
from urllib.parse import quote


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


def fetch_quizzes_folder_id(course_id: str, access_token: str) -> Optional[str]:
    """
    Fetch the Quizzes folder ID from Canvas course files.
    
    Args:
        course_id: Canvas course ID
        access_token: Canvas API access token
        
    Returns:
        String ID of the Quizzes folder or None if not found
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    base_url = "https://umich.instructure.com/api/v1"
    url = f"{base_url}/courses/{course_id}/folders"
    
    try:
        while url:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            folders = response.json()
            
            # Look for "Quizzes" folder
            for folder in folders:
                folder_name = folder.get("name", "")
                if folder_name.lower() == "quizzes":
                    return str(folder.get("id"))
            
            # Check for pagination
            links = response.headers.get("Link", "")
            url = None
            for link in links.split(","):
                if 'rel="next"' in link:
                    url = link.split(";")[0].strip("<>")
                    break
                    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching folders: {e}")
        return None
    except Exception as e:
        print(f"Error processing folders: {e}")
        return None
        
    return None


def fetch_quiz_folder_id(course_id: str, access_token: str, quiz_number: str) -> Optional[str]:
    """
    Fetch the specific quiz folder ID (e.g., Quiz 1) from the Quizzes folder.
    
    Args:
        course_id: Canvas course ID
        access_token: Canvas API access token
        quiz_number: Quiz number (e.g., "1", "2", "3")
        
    Returns:
        String ID of the quiz folder or None if not found
    """
    # First get the Quizzes folder ID
    quizzes_folder_id = fetch_quizzes_folder_id(course_id, access_token)
    if not quizzes_folder_id:
        print("Warning: Could not find 'Quizzes' folder in Canvas course")
        return None
    
    headers = {"Authorization": f"Bearer {access_token}"}
    base_url = "https://umich.instructure.com/api/v1"
    url = f"{base_url}/folders/{quizzes_folder_id}/folders"
    
    # Format quiz folder name
    quiz_folder_name = f"Quiz {quiz_number}"
    
    try:
        while url:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            folders = response.json()
            
            # Look for specific quiz folder (e.g., "Quiz 1")
            for folder in folders:
                folder_name = folder.get("name", "")
                if folder_name.lower() == quiz_folder_name.lower():
                    print(f"Found quiz folder {folder_name} with ID: {folder.get('id')}")
                    return str(folder.get("id"))
            
            # Check for pagination
            links = response.headers.get("Link", "")
            url = None
            for link in links.split(","):
                if 'rel="next"' in link:
                    url = link.split(";")[0].strip("<>")
                    break
                    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching quiz folders: {e}")
        return None
    except Exception as e:
        print(f"Error processing quiz folders: {e}")
        return None
        
    print(f"Warning: Could not find quiz folder for Quiz {quiz_number}")
    return None


def fetch_sample_quiz_folder_url(course_id: str, access_token: str, quiz_number: str) -> Optional[str]:
    """
    Fetch the sample quiz folder URL for a given quiz number.
    The folder structure is: Quizzes/Quiz N/Quiz N Sample
    
    Args:
        course_id: Canvas course ID
        access_token: Canvas API access token
        quiz_number: Quiz number (e.g., "1", "2", "3")
        
    Returns:
        URL to the sample quiz folder or None if not found
    """
    # First get the Quiz N folder ID
    quiz_folder_id = fetch_quiz_folder_id(course_id, access_token, quiz_number)
    if not quiz_folder_id:
        return None
    
    headers = {"Authorization": f"Bearer {access_token}"}
    base_url = "https://umich.instructure.com/api/v1"
    url = f"{base_url}/folders/{quiz_folder_id}/folders"
    
    # Look for "Quiz N Sample" subfolder
    sample_folder_name = f"Quiz {quiz_number} Sample"
    
    try:
        while url:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            folders = response.json()
            
            # Look for the sample subfolder
            for folder in folders:
                folder_name = folder.get("name", "")
                if folder_name.lower() == sample_folder_name.lower():
                    # Generate the Canvas folder URL
                    # Format: /courses/{course_id}/files/folder/Quizzes/Quiz%20{N}/Quiz%20{N}%20Sample
                    folder_url = f"https://umich.instructure.com/courses/{course_id}/files/folder/Quizzes/Quiz%20{quiz_number}/Quiz%20{quiz_number}%20Sample"
                    print(f"Found sample quiz folder: Quiz {quiz_number} Sample -> {folder_url}")
                    return folder_url
            
            # Check for pagination
            links = response.headers.get("Link", "")
            url = None
            for link in links.split(","):
                if 'rel="next"' in link:
                    url = link.split(";")[0].strip("<>")
                    break
                    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching sample quiz folder: {e}")
        return None
    except Exception as e:
        print(f"Error processing sample quiz folder: {e}")
        return None
    
    print(f"Warning: Could not find sample PDF for Quiz {quiz_number}")
    return None


def fetch_all_sample_quiz_folder_urls(course_id: str, access_token: str, max_quizzes: int = 10) -> Dict[str, str]:
    """
    Fetch sample quiz folder URLs for all quizzes (up to max_quizzes).
    
    Args:
        course_id: Canvas course ID
        access_token: Canvas API access token
        max_quizzes: Maximum number of quizzes to check (default 10)
        
    Returns:
        Dictionary mapping quiz numbers (as strings) to folder URLs
    """
    sample_quiz_urls = {}
    
    if not course_id or not access_token:
        print("Warning: Missing course_id or access_token for Canvas API call")
        return sample_quiz_urls
    
    print("Fetching sample quiz folder URLs from Canvas...")
    
    # First, check that the Quizzes folder exists
    quizzes_folder_id = fetch_quizzes_folder_id(course_id, access_token)
    if not quizzes_folder_id:
        print("Warning: Could not find 'Quizzes' folder in Canvas course")
        return sample_quiz_urls
    
    print(f"Found Quizzes folder with ID: {quizzes_folder_id}")
    
    # Fetch all quiz folders to see which ones exist
    headers = {"Authorization": f"Bearer {access_token}"}
    base_url = "https://umich.instructure.com/api/v1"
    url = f"{base_url}/folders/{quizzes_folder_id}/folders"
    
    quiz_numbers = []
    
    try:
        while url:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            folders = response.json()
            
            # Find quiz folders (e.g., "Quiz 1", "Quiz 2")
            for folder in folders:
                folder_name = folder.get("name", "")
                # Look for "Quiz N" pattern
                match = re.search(r"Quiz\s+(\d+)", folder_name, re.IGNORECASE)
                if match:
                    quiz_number = match.group(1)
                    quiz_numbers.append(quiz_number)
                    print(f"Found quiz folder: {folder_name} (Quiz {quiz_number})")
            
            # Check for pagination
            links = response.headers.get("Link", "")
            url = None
            for link in links.split(","):
                if 'rel="next"' in link:
                    url = link.split(";")[0].strip("<>")
                    break
                    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching quiz folders: {e}")
        return sample_quiz_urls
    except Exception as e:
        print(f"Error processing quiz folders: {e}")
        return sample_quiz_urls
    
    # For each quiz folder found, try to get the sample folder URL
    for quiz_number in quiz_numbers:
        sample_url = fetch_sample_quiz_folder_url(course_id, access_token, quiz_number)
        if sample_url:
            sample_quiz_urls[quiz_number] = sample_url
    
    print(f"Fetched sample PDFs for {len(sample_quiz_urls)} quizzes")
    
    return sample_quiz_urls 