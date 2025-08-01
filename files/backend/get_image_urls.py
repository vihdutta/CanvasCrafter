import requests
import re
from typing import Dict, Optional
from urllib.parse import quote


def fetch_site_data_folder_id(course_id: str, access_token: str) -> Optional[str]:
    headers = {"Authorization": f"Bearer {access_token}"}
    base_url = "https://umich.instructure.com/api/v1"
    url = f"{base_url}/courses/{course_id}/folders"
    
    try:
        while url:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            folders = response.json()
            
            # Look for "Site Data" folder
            for folder in folders:
                folder_name = folder.get("name", "")
                if folder_name.lower() == "site data":
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


def fetch_image_urls_from_site_data(course_id: str, access_token: str, image_names: list) -> Dict[str, str]:
    image_urls = {}
    
    if not course_id or not access_token:
        print("Warning: Missing course_id or access_token for Canvas API call")
        return image_urls
    
    # First, get the Site Data folder ID
    site_data_folder_id = fetch_site_data_folder_id(course_id, access_token)
    if not site_data_folder_id:
        print("Warning: Could not find 'Site Data' folder in Canvas course")
        return image_urls
    
    print(f"Found Site Data folder with ID: {site_data_folder_id}")
    
    headers = {"Authorization": f"Bearer {access_token}"}
    base_url = "https://umich.instructure.com/api/v1"
    url = f"{base_url}/folders/{site_data_folder_id}/files"
    
    try:
        while url:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            files = response.json()
            
            # Process each file to find matching image names
            for file_info in files:
                file_name = file_info.get("display_name", "")
                file_id = file_info.get("id")
                
                # Check if this file name matches any of our target image names
                for target_name in image_names:
                    if file_name == target_name:
                        # Create the Canvas preview URL
                        preview_url = f"https://umich.instructure.com/courses/{course_id}/files/{file_id}/preview"
                        image_urls[target_name] = preview_url
                        print(f"Found image: {target_name} -> {preview_url}")
                        break
            
            # Check for pagination
            links = response.headers.get("Link", "")
            url = None
            for link in links.split(","):
                if 'rel="next"' in link:
                    url = link.split(";")[0].strip("<>")
                    break
                    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching files from Site Data folder: {e}")
    except Exception as e:
        print(f"Error processing files from Site Data folder: {e}")
    
    # Log any missing images
    missing_images = set(image_names) - set(image_urls.keys())
    if missing_images:
        print(f"Warning: Could not find the following images in Site Data folder: {missing_images}")
    
    return image_urls


def get_image_urls_for_yaml_data(images_data: Dict, course_id: str = None, access_token: str = None) -> Dict:    
    # Extract all image names from the YAML data
    image_names = []
    for week_data in images_data.values():
        if "image_name" in week_data:
            image_names.append(week_data["image_name"])
    
    # Fetch the URLs from Canvas
    image_urls = fetch_image_urls_from_site_data(course_id, access_token, image_names)
    
    # Update the images_data with the fetched URLs
    updated_images_data = {}
    for week_key, week_data in images_data.items():
        updated_data = week_data.copy()
        image_name = week_data.get("image_name")
        
        if image_name and image_name in image_urls:
            # Replace image_name with image_path containing the Canvas URL
            updated_data["image_path"] = image_urls[image_name]
            # Keep image_name for reference if needed
            updated_data["image_name"] = image_name
        else:
            # If we can't find the image, provide a fallback or warning
            print(f"Warning: Could not find Canvas URL for image '{image_name}' in week {week_key}")
            # Keep the original image_name and add a placeholder path
            updated_data["image_path"] = f"https://via.placeholder.com/400x300?text={quote(image_name or 'Image Not Found')}"
            updated_data["image_name"] = image_name
            
        updated_images_data[week_key] = updated_data
    
    return updated_images_data
