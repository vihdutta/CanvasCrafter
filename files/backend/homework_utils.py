import requests
import re
from typing import Dict, Optional, List
from urllib.parse import quote


def fetch_assignments_folder_id(course_id: str, access_token: str) -> Optional[str]:
    """
    Fetch the Assignments folder ID from Canvas course files.
    
    Args:
        course_id: Canvas course ID
        access_token: Canvas API access token
        
    Returns:
        String ID of the Assignments folder or None if not found
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    base_url = "https://umich.instructure.com/api/v1"
    url = f"{base_url}/courses/{course_id}/folders"
    
    try:
        while url:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            folders = response.json()
            
            # Look for "Assignments" folder
            for folder in folders:
                folder_name = folder.get("name", "")
                if folder_name.lower() == "assignments":
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


def fetch_homework_folder_id(course_id: str, access_token: str, homework_number: str) -> Optional[str]:
    """
    Fetch the specific homework folder ID (e.g., HW01) from the Assignments folder.
    
    Args:
        course_id: Canvas course ID
        access_token: Canvas API access token
        homework_number: Homework number (e.g., "1", "2", "10")
        
    Returns:
        String ID of the homework folder or None if not found
    """
    # First get the Assignments folder ID
    assignments_folder_id = fetch_assignments_folder_id(course_id, access_token)
    if not assignments_folder_id:
        print("Warning: Could not find 'Assignments' folder in Canvas course")
        return None
    
    headers = {"Authorization": f"Bearer {access_token}"}
    base_url = "https://umich.instructure.com/api/v1"
    url = f"{base_url}/folders/{assignments_folder_id}/folders"
    
    # Format homework number with leading zero if needed
    hw_folder_name = f"HW{int(homework_number):02d}"
    
    try:
        while url:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            folders = response.json()
            
            # Look for specific homework folder (e.g., "HW01")
            for folder in folders:
                folder_name = folder.get("name", "")
                if folder_name.upper() == hw_folder_name.upper():
                    return str(folder.get("id"))
            
            # Check for pagination
            links = response.headers.get("Link", "")
            url = None
            for link in links.split(","):
                if 'rel="next"' in link:
                    url = link.split(";")[0].strip("<>")
                    break
                    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching homework folders: {e}")
        return None
    except Exception as e:
        print(f"Error processing homework folders: {e}")
        return None
        
    return None


def fetch_homework_pdf_links(course_id: str, access_token: str, homework_number: str) -> Dict[str, str]:
    """
    Fetch the homework PDF and solution PDF links for a specific homework assignment.
    
    Args:
        course_id: Canvas course ID
        access_token: Canvas API access token
        homework_number: Homework number (e.g., "1", "2", "10")
        
    Returns:
        Dictionary with keys 'homework_pdf' and 'solution_pdf' containing Canvas URLs
    """
    pdf_links = {
        "homework_pdf": "",
        "solution_pdf": ""
    }
    
    if not course_id or not access_token:
        print("Warning: Missing course_id or access_token for Canvas API call")
        return pdf_links
    
    # Get the homework folder ID
    homework_folder_id = fetch_homework_folder_id(course_id, access_token, homework_number)
    if not homework_folder_id:
        print(f"Warning: Could not find homework folder for HW{int(homework_number):02d}")
        return pdf_links
    
    print(f"Found homework folder HW{int(homework_number):02d} with ID: {homework_folder_id}")
    
    headers = {"Authorization": f"Bearer {access_token}"}
    base_url = "https://umich.instructure.com/api/v1"
    url = f"{base_url}/folders/{homework_folder_id}/files"
    
    hw_formatted = f"HW{int(homework_number):02d}"
    
    try:
        while url:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            files = response.json()
            
            # Process each file to find homework and solution PDFs
            for file_info in files:
                file_name = file_info.get("display_name", "")
                file_id = file_info.get("id")
                
                # Check if this is a PDF file
                if not file_name.lower().endswith('.pdf'):
                    continue
                
                # Create the Canvas preview URL
                preview_url = f"https://umich.instructure.com/courses/{course_id}/files/{file_id}/preview"
                
                # Check if this is the homework PDF (contains HW## but not "Solutions")
                if hw_formatted.upper() in file_name.upper() and "SOLUTIONS" not in file_name.upper():
                    pdf_links["homework_pdf"] = preview_url
                    print(f"Found homework PDF: {file_name} -> {preview_url}")
                
                # Check if this is the solution PDF (contains HW##_Solutions)
                elif hw_formatted.upper() in file_name.upper() and "SOLUTIONS" in file_name.upper():
                    pdf_links["solution_pdf"] = preview_url
                    print(f"Found solution PDF: {file_name} -> {preview_url}")
            
            # Check for pagination
            links = response.headers.get("Link", "")
            url = None
            for link in links.split(","):
                if 'rel="next"' in link:
                    url = link.split(";")[0].strip("<>")
                    break
                    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching files from homework folder: {e}")
    except Exception as e:
        print(f"Error processing files from homework folder: {e}")
    
    # Log any missing PDFs
    missing_pdfs = []
    if not pdf_links["homework_pdf"]:
        missing_pdfs.append(f"homework PDF for {hw_formatted}")
    if not pdf_links["solution_pdf"]:
        missing_pdfs.append(f"solution PDF for {hw_formatted}")
    
    if missing_pdfs:
        print(f"Warning: Could not find the following PDFs in {hw_formatted} folder: {missing_pdfs}")
    
    return pdf_links


def get_all_homework_pdf_links(course_id: str, access_token: str, homework_numbers: List[str]) -> Dict[str, Dict[str, str]]:
    """
    Get PDF links for multiple homework assignments.
    
    Args:
        course_id: Canvas course ID
        access_token: Canvas API access token
        homework_numbers: List of homework numbers (e.g., ["1", "2", "3"])
        
    Returns:
        Dictionary with homework numbers as keys and PDF link dictionaries as values
        Example: {"1": {"homework_pdf": "url1", "solution_pdf": "url2"}, "2": {...}}
    """
    all_pdf_links = {}
    
    for hw_number in homework_numbers:
        hw_key = f"HW{int(hw_number):02d}"
        pdf_links = fetch_homework_pdf_links(course_id, access_token, hw_number)
        all_pdf_links[hw_key] = pdf_links
    
    return all_pdf_links


def extract_homework_numbers_from_weeks_data(weeks_data: Dict) -> List[str]:
    """
    Extract all homework numbers found in the weeks data.
    
    Args:
        weeks_data: Dictionary containing all weeks data
        
    Returns:
        List of homework numbers as strings
    """
    homework_numbers = set()
    
    for week_num, week_data in weeks_data.items():
        # Skip non-numeric keys like 'icon_urls'
        if not str(week_num).isdigit():
            continue
            
        # Check each day of the week for homework assignments
        for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
            if day in week_data:
                day_data = week_data[day]
                
                # Check assigned homework
                assigned_text = day_data.get("assigned", "")
                if assigned_text and "HW" in str(assigned_text).upper():
                    hw_match = re.search(r'HW\s*(\d+)', str(assigned_text), re.IGNORECASE)
                    if hw_match:
                        homework_numbers.add(hw_match.group(1))
                
                # Check due homework
                due_text = day_data.get("due", "")
                if due_text and "HW" in str(due_text).upper():
                    hw_match = re.search(r'HW\s*(\d+)', str(due_text), re.IGNORECASE)
                    if hw_match:
                        homework_numbers.add(hw_match.group(1))
    
    return sorted(list(homework_numbers), key=int)
