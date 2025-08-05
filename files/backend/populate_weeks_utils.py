import re
import requests
import pandas as pd
from typing import Optional, Dict, List


def title_to_url_safe(title: str) -> str:
    if not title or pd.isna(title) or str(title).strip() == "":
        return ""
    url_safe = str(title).lower()
    url_safe = re.sub(r'[^a-z0-9]+', '-', url_safe)
    url_safe = re.sub(r'-+', '-', url_safe)
    url_safe = url_safe.strip('-')
    
    return url_safe


def get_week_title_with_topic_and_date(weeks_data: Dict, display_week_num: int) -> str:
    """
    Generate week title in format: "Week #: <topic> (MM/DD/YYYY)"
    
    Args:
        weeks_data: Dictionary containing all weeks data
        display_week_num: The adjusted week number (e.g., 101, 102, etc.)
    
    Returns:
        Formatted title string
    """
    # Convert display week number back to original week number (subtract 16)
    original_week_num = display_week_num - 16
    
    if original_week_num not in weeks_data:
        return f"Week {display_week_num}"
    
    week_data = weeks_data[original_week_num]
    
    # Find the first topic and earliest date from the week's days
    topic = ""
    earliest_date = ""
    
    weekday_order = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    
    for weekday in weekday_order:
        if weekday in week_data:
            day_data = week_data[weekday]
            
            # Get the first non-empty topic found
            if not topic and "topic" in day_data and day_data["topic"]:
                topic = str(day_data["topic"]).strip()
            
            # Get the earliest date found
            if not earliest_date and "date" in day_data and day_data["date"]:
                earliest_date = str(day_data["date"]).strip()
                break  # Since we iterate in order, first date found is earliest
    
    # Format the title
    if topic and earliest_date:
        return f"Week {display_week_num}: {topic} ({earliest_date})"
    elif topic:
        return f"Week {display_week_num}: {topic}"
    else:
        return f"Week {display_week_num}"


def fetch_canvas_pages(course_id: str, access_token: str) -> Dict[str, str]:
    quiz_pages = {}
    
    if not course_id or not access_token:
        print("Warning: Missing course_id or access_token for Canvas API call")
        return quiz_pages
    
    headers = {"Authorization": f"Bearer {access_token}"}
    base_url = "https://umich.instructure.com/api/v1"
    url = f"{base_url}/courses/{course_id}/pages"
    
    try:
        while url:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            pages = response.json()
            
            # Process each page to find quiz pages
            for page in pages:
                title = page.get("title", "")
                page_url = page.get("url", "")
                
                # Look for "Quiz #" pattern in page titles (case-insensitive)
                quiz_pattern = r'Quiz\s*(\d+)'
                match = re.search(quiz_pattern, title, re.IGNORECASE)
                
                if match:
                    quiz_number = match.group(1)
                    # Create full Canvas page URL
                    canvas_url = f"https://umich.instructure.com/courses/{course_id}/pages/{page_url}"
                    quiz_pages[quiz_number] = canvas_url
                    print(f"Found sample quiz page: Quiz {quiz_number} -> {title}")
            
            # Check for pagination
            links = response.headers.get("Link", "")
            url = None
            for link in links.split(","):
                if 'rel="next"' in link:
                    url = link.split(";")[0].strip("<>")
                    break
                    
    except requests.exceptions.RequestException as e:
        print(f"Warning: Failed to fetch Canvas pages: {e}")
    except Exception as e:
        print(f"Warning: Error processing Canvas pages: {e}")
    
    return quiz_pages


def process_quiz_from_topic(topic: str, sample_quiz_urls: Optional[Dict[str, str]] = None) -> dict:
    quiz_info = {
        "has_quiz": False,
        "quiz_number": "",
        "study_text": "",
        "sample_text": "",
        "sample_quiz_url": ""
    }
    
    if not topic or pd.isna(topic):
        return quiz_info
    
    topic_str = str(topic).strip()
    
    # Look for "Quiz" followed by optional space and a number
    quiz_pattern = r'Quiz\s*(\d+)'
    match = re.search(quiz_pattern, topic_str, re.IGNORECASE)
    
    if match:
        quiz_number = match.group(1)
        quiz_info["has_quiz"] = True
        quiz_info["quiz_number"] = quiz_number
        quiz_info["study_text"] = f"Study for Quiz {quiz_number}"
        quiz_info["sample_text"] = f"Sample Quiz {quiz_number}"
        
        # Add sample quiz URL if available
        if sample_quiz_urls and quiz_number in sample_quiz_urls:
            quiz_info["sample_quiz_url"] = sample_quiz_urls[quiz_number]
    
    return quiz_info 

def collect_quiz_dates(weeks_data: Dict) -> List[Dict]:
    """
    Collect all quiz dates from the weeks data structure.
    
    Args:
        weeks_data: Dictionary containing all weeks data
        
    Returns:
        List of quiz dictionaries with quiz_number, date, and week_number
        sorted by date
    """
    quizzes = []
    
    for week_num, week_data in weeks_data.items():
        # Check each day of the week for quizzes
        for day in ["monday", "wednesday", "friday"]:  # Only class days
            if day in week_data:
                day_data = week_data[day]
                quiz_info = day_data.get("quiz_info", {})
                
                if quiz_info.get("has_quiz", False):
                    quiz_number = quiz_info.get("quiz_number", "")
                    date = day_data.get("date", "")
                    
                    if quiz_number and date:
                        quizzes.append({
                            "quiz_number": int(quiz_number),
                            "date": date,
                            "week_number": week_num,
                            "day": day
                        })
    
    # Sort by quiz number to ensure proper ordering
    quizzes.sort(key=lambda x: x["quiz_number"])
    return quizzes

def find_next_quiz(weeks_data: Dict, current_week_num: int) -> Optional[Dict]:
    """
    Find the next upcoming quiz based on the current week.
    
    Args:
        weeks_data: Dictionary containing all weeks data
        current_week_num: Current week number
        
    Returns:
        Dictionary with next quiz info or None if no upcoming quiz
    """
    from datetime import datetime
    
    all_quizzes = collect_quiz_dates(weeks_data)
    
    if not all_quizzes:
        return None
    
    # Get current week's date to determine what has passed
    current_date = None
    current_week_data = weeks_data.get(current_week_num, {})
    
    # Find the earliest date in the current week as reference
    for day in ["monday", "wednesday", "friday"]:
        if day in current_week_data and current_week_data[day].get("date"):
            current_date = current_week_data[day]["date"]
            break
    
    if not current_date:
        # If no current date found, return the first quiz
        return all_quizzes[0] if all_quizzes else None
    
    # Parse current date
    try:
        current_date_obj = datetime.strptime(current_date, "%m/%d/%Y")
    except ValueError:
        # If parsing fails, return the first quiz
        return all_quizzes[0] if all_quizzes else None
    
    # Find the next quiz that hasn't passed yet
    for quiz in all_quizzes:
        try:
            quiz_date_obj = datetime.strptime(quiz["date"], "%m/%d/%Y")
            if quiz_date_obj >= current_date_obj:
                return quiz
        except ValueError:
            continue
    
    # If all quizzes have passed, return None
    return None 