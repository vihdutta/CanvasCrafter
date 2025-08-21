import requests
from typing import Dict, Optional


def fetch_course_information_folder_id(course_id: str, access_token: str) -> Optional[str]:
    """Fetch the 'Course Information' folder ID from Canvas."""
    headers = {"Authorization": f"Bearer {access_token}"}
    base_url = "https://umich.instructure.com/api/v1"
    url = f"{base_url}/courses/{course_id}/folders"
    
    try:
        while url:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            folders = response.json()
            
            # Look for "Course Information" folder
            for folder in folders:
                folder_name = folder.get("name", "")
                if folder_name.lower() == "course information":
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


def fetch_course_pdfs(course_id: str, access_token: str) -> Dict[str, str]:
    """
    Fetch PDF file URLs from the 'Course Information' folder.
    Returns URLs for syllabus schedule and syllabus PDFs.
    """
    pdf_urls = {}
    
    if not course_id or not access_token:
        print("Warning: Missing course_id or access_token for Canvas API call")
        return pdf_urls
    
    # First, get the Course Information folder ID
    course_info_folder_id = fetch_course_information_folder_id(course_id, access_token)
    if not course_info_folder_id:
        print("Warning: Could not find 'Course Information' folder in Canvas course")
        return pdf_urls
    
    print(f"Found Course Information folder with ID: {course_info_folder_id}")
    
    headers = {"Authorization": f"Bearer {access_token}"}
    base_url = "https://umich.instructure.com/api/v1"
    url = f"{base_url}/folders/{course_info_folder_id}/files"
    
    try:
        while url:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            files = response.json()
            
            # Process each file to find PDFs with the specified substrings
            for file_info in files:
                file_name = file_info.get("display_name", "")
                file_id = file_info.get("id")
                
                # Check if this is a PDF file
                if not file_name.lower().endswith('.pdf'):
                    continue
                
                # Create the Canvas preview URL
                preview_url = f"https://umich.instructure.com/courses/{course_id}/files/{file_id}/preview"
                
                # Check for syllabus schedule PDF (contains "ME240_SyllabusSchedule_")
                if "ME240_SyllabusSchedule_" in file_name:
                    pdf_urls["syllabus_schedule"] = preview_url
                    print(f"Found syllabus schedule PDF: {file_name} -> {preview_url}")
                
                # Check for syllabus PDF (contains "ME240_Syllabus_")
                elif "ME240_Syllabus_" in file_name:
                    pdf_urls["syllabus"] = preview_url
                    print(f"Found syllabus PDF: {file_name} -> {preview_url}")
            
            # Check for pagination
            links = response.headers.get("Link", "")
            url = None
            for link in links.split(","):
                if 'rel="next"' in link:
                    url = link.split(";")[0].strip("<>")
                    break
                    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching files from Course Information folder: {e}")
    except Exception as e:
        print(f"Error processing files from Course Information folder: {e}")
    
    # Log any missing PDFs
    missing_pdfs = []
    if "syllabus_schedule" not in pdf_urls:
        missing_pdfs.append("Syllabus Schedule (ME240_SyllabusSchedule_)")
    if "syllabus" not in pdf_urls:
        missing_pdfs.append("Syllabus (ME240_Syllabus_)")
    
    if missing_pdfs:
        print(f"Warning: Could not find the following PDFs in Course Information folder: {missing_pdfs}")
    
    return pdf_urls
