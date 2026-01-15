import re
import requests
import pandas as pd
from typing import Optional, Dict, List


def title_to_url_safe(title: str) -> str:
    if not title or pd.isna(title) or str(title).strip() == "":
        return ""
    url_safe = str(title).lower()
    # Replace forward slashes with "-slash-" first
    url_safe = url_safe.replace("/", "-slash-")
    # Remove apostrophes completely
    url_safe = url_safe.replace("'", "")
    # Replace ampersand with "and"
    url_safe = url_safe.replace("&", "and")
    # Then replace all other non-alphanumeric characters with hyphens
    url_safe = re.sub(r"[^a-z0-9]+", "-", url_safe)
    url_safe = re.sub(r"-+", "-", url_safe)
    url_safe = url_safe.strip("-")

    return url_safe


def get_week_title_with_topic_and_date(weeks_data: Dict, display_week_num: int) -> str:
    """
    Generate week title in format: "Week #: <topic> (MM/DD/YYYY)"
    If quiz or checkout is found in the week, append it to the title.

    Args:
        weeks_data: Dictionary containing all weeks data
        display_week_num: The adjusted week number (e.g., 37, 38, etc.)

    Returns:
        Formatted title string
    """
    # Convert display week number back to original week number (subtract 36)
    original_week_num = display_week_num

    if original_week_num not in weeks_data:
        return f"Week {display_week_num}"

    week_data = weeks_data[original_week_num]

    # Find the first topic and earliest date from the week's days
    topic = ""
    earliest_date = ""

    weekday_order = [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]

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

    # Check for quiz or checkout in this week
    quiz_checkout_info = find_quiz_or_checkout_in_week(week_data)

    # Format the title
    if topic and earliest_date:
        base_title = f"Week {display_week_num}: {topic} ({earliest_date})"
    elif topic:
        base_title = f"Week {display_week_num}: {topic}"
    else:
        base_title = f"Week {display_week_num}"

    # Append quiz/checkout info if found
    if quiz_checkout_info:
        base_title += f" - {quiz_checkout_info}"

    return base_title


def find_quiz_or_checkout_in_week(week_data: Dict) -> str:
    """
    Find quiz or checkout topics in a week and return formatted string.
    Returns early if one is found.

    Args:
        week_data: Dictionary containing week data

    Returns:
        Formatted string with quiz/checkout info or empty string if none found
    """
    weekday_order = [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]

    for weekday in weekday_order:
        if weekday in week_data:
            day_data = week_data[weekday]
            topic = day_data.get("topic", "")

            if not topic:
                continue

            topic_str = str(topic).strip().upper()

            # Check for QUIZ
            if "QUIZ" in topic_str:
                # Extract quiz number
                import re

                quiz_match = re.search(r"QUIZ\s*(\d+)", topic_str)
                if quiz_match:
                    quiz_number = quiz_match.group(1)
                    return f"Quiz {quiz_number}"
                else:
                    return "Quiz"

            # Check for CHECKOUT
            elif "CHECKOUT" in topic_str:
                # Extract checkout number
                import re

                checkout_match = re.search(r"CHECKOUT\s*(\d+)", topic_str)
                if checkout_match:
                    checkout_number = checkout_match.group(1)
                    return f"Checkout {checkout_number}"
                else:
                    return "Checkout"

    return ""


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

                # Look for "Quiz#" or "Quiz #" pattern in page titles (case-insensitive)
                quiz_pattern = r"Quiz\s*(\d+)"
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


def process_quiz_from_topic(
    topic: str, sample_quiz_urls: Optional[Dict[str, str]] = None
) -> dict:
    quiz_info = {
        "has_quiz": False,
        "quiz_number": "",
        "study_text": "",
        "sample_text": "",
        "sample_quiz_url": "",
    }

    if not topic or pd.isna(topic):
        return quiz_info

    topic_str = str(topic).strip()

    # Look for "Quiz" followed by optional space and a number
    quiz_pattern = r"Quiz\s*(\d+)"
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


def process_checkout_from_topic(topic: str) -> dict:
    """
    Extract checkout information from a topic string.
    Returns a dict with keys: has_checkout (bool) and checkout_number (str).
    """
    checkout_info = {
        "has_checkout": False,
        "checkout_number": "",
    }
    if not topic or pd.isna(topic):
        return checkout_info

    topic_str = str(topic).strip()

    # Look for "Checkout" followed by optional space and a number
    checkout_pattern = r"Checkout\s*(\d+)"
    match = re.search(checkout_pattern, topic_str, re.IGNORECASE)

    if match:
        checkout_number = match.group(1)
        checkout_info["has_checkout"] = True
        checkout_info["checkout_number"] = checkout_number

    return checkout_info


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
        # Check each lecture day for quizzes
        from files.backend.populate_weeks import get_lecture_days_list

        lecture_days = get_lecture_days_list()
        for day in lecture_days:
            if day in week_data:
                day_data = week_data[day]
                quiz_info = day_data.get("quiz_info", {})

                if quiz_info.get("has_quiz", False):
                    quiz_number = quiz_info.get("quiz_number", "")
                    date = day_data.get("date", "")

                    if quiz_number and date:
                        quizzes.append(
                            {
                                "quiz_number": int(quiz_number),
                                "date": date,
                                "week_number": week_num,
                                "day": day,
                            }
                        )

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
    from files.backend.populate_weeks import get_lecture_days_list

    lecture_days = get_lecture_days_list()
    for day in lecture_days:
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


def find_next_checkout(weeks_data: Dict, current_week_num: int) -> Optional[Dict]:
    """
    Find the next upcoming checkout based on the current week.

    Args:
        weeks_data: Dictionary containing all weeks data
        current_week_num: Current week number

    Returns:
        Dictionary with next checkout info or None if no upcoming checkout
    """
    from datetime import datetime
    from files.backend.checkout_utils import collect_checkout_assignments

    all_checkouts = collect_checkout_assignments(weeks_data)

    if not all_checkouts:
        return None

    # Get current week's date to determine what has passed
    current_date = None
    current_week_data = weeks_data.get(current_week_num, {})

    # Find the earliest date in the current week as reference
    from files.backend.populate_weeks import get_lecture_days_list

    lecture_days = get_lecture_days_list()
    for day in lecture_days:
        if day in current_week_data and current_week_data[day].get("date"):
            current_date = current_week_data[day]["date"]
            break

    if not current_date:
        # If no current date found, return the first checkout
        return all_checkouts[0] if all_checkouts else None

    # Parse current date
    try:
        current_date_obj = datetime.strptime(current_date, "%m/%d/%Y")
    except ValueError:
        # If parsing fails, return the first checkout
        return all_checkouts[0] if all_checkouts else None

    # Find the next checkout that hasn't passed yet
    for checkout in all_checkouts:
        try:
            checkout_date_obj = datetime.strptime(checkout["date"], "%m/%d/%Y")
            if checkout_date_obj >= current_date_obj:
                return checkout
        except ValueError:
            continue

    # If all checkouts have passed, return None
    return None


def collect_homework_assignments_opening_during_week(
    weeks_data: Dict, current_week_num: int
) -> List[Dict]:
    """
    Collect homework assignments that are being assigned/opened during the specified week.

    Args:
        weeks_data: Dictionary containing all weeks data
        current_week_num: Week number to check for homework assignments being opened

    Returns:
        List of homework dictionaries with homework_number, assigned_date, due_date, day
    """
    if current_week_num not in weeks_data:
        return []

    week_data = weeks_data[current_week_num]
    homework_opening = []

    # Check each day of the week for homework assignments being opened
    for day in [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]:
        if day in week_data:
            day_data = week_data[day]
            assigned_text = day_data.get("assigned", "")

            if assigned_text and "HW" in str(assigned_text).upper():
                # Extract homework number using regex
                hw_match = re.search(r"HW\s*(\d+)", str(assigned_text), re.IGNORECASE)
                if hw_match:
                    hw_number = hw_match.group(1)

                    # Find due date for this homework across all weeks
                    due_date = find_homework_due_date_across_weeks(
                        weeks_data, hw_number
                    )

                    homework_opening.append(
                        {
                            "homework_number": hw_number,
                            "assigned_date": day_data.get("date", ""),
                            "due_date": due_date,
                            "day": day,
                            "homework_key": f"HW{int(hw_number):02d}",
                            "homework_name": f"HOMEWORK {hw_number}",
                        }
                    )

    return homework_opening


def collect_homework_assignments_due_during_week(
    weeks_data: Dict, current_week_num: int
) -> List[Dict]:
    """
    Collect homework assignments that are due during the specified week.

    Args:
        weeks_data: Dictionary containing all weeks data
        current_week_num: Week number to check for homework assignments due

    Returns:
        List of homework dictionaries with homework_number, due_date, assigned_date, day
    """
    if current_week_num not in weeks_data:
        return []

    week_data = weeks_data[current_week_num]
    homework_due = []

    # Check each day of the week for homework assignments due
    for day in [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]:
        if day in week_data:
            day_data = week_data[day]
            due_text = day_data.get("due", "")

            if due_text and "HW" in str(due_text).upper():
                # Extract homework number using regex
                hw_match = re.search(r"HW\s*(\d+)", str(due_text), re.IGNORECASE)
                if hw_match:
                    hw_number = hw_match.group(1)

                    # Find assigned date for this homework across all weeks
                    assigned_date = find_homework_assigned_date_across_weeks(
                        weeks_data, hw_number
                    )

                    homework_due.append(
                        {
                            "homework_number": hw_number,
                            "due_date": day_data.get("date", ""),
                            "assigned_date": assigned_date,
                            "day": day,
                            "homework_key": f"HW{int(hw_number):02d}",
                            "homework_name": f"HOMEWORK {hw_number}",
                        }
                    )

    return homework_due


def find_homework_due_date_across_weeks(weeks_data: Dict, hw_number: str) -> str:
    """Find the due date for a specific homework number across all weeks."""
    for week_num, week_data in weeks_data.items():
        # Skip non-numeric keys like 'icon_urls'
        if not str(week_num).isdigit():
            continue

        for day in [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]:
            if day in week_data and "due" in week_data[day]:
                due_text = week_data[day]["due"]
                if due_text and hw_number in str(due_text):
                    return week_data[day]["date"]

    return "TBD"


def find_homework_assigned_date_across_weeks(weeks_data: Dict, hw_number: str) -> str:
    """Find the assigned date for a specific homework number across all weeks."""
    for week_num, week_data in weeks_data.items():
        # Skip non-numeric keys like 'icon_urls'
        if not str(week_num).isdigit():
            continue

        for day in [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]:
            if day in week_data and "assigned" in week_data[day]:
                assigned_text = week_data[day]["assigned"]
                if assigned_text and hw_number in str(assigned_text):
                    return week_data[day]["date"]

    return "TBD"


def get_week_days_in_order(week_data: Dict) -> List[Dict]:
    """
    Extract the days present in a week's data, sorted by date.
    Returns a list of dicts with 'day_name', 'display_name', 'date', and all day data.
    
    Args:
        week_data: Dictionary containing a single week's data
        
    Returns:
        List of day dictionaries sorted by date, each containing:
        - day_name: lowercase day name (e.g., 'monday')
        - display_name: capitalized day name (e.g., 'Monday')
        - date: the formatted date string
        - data: the full day data dictionary
    """
    from datetime import datetime
    
    weekday_order = [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]
    
    days_found = []
    
    for day_name in weekday_order:
        if day_name in week_data and isinstance(week_data[day_name], dict):
            day_data = week_data[day_name]
            date_str = day_data.get("date", "")
            
            # Parse the date for sorting
            date_obj = None
            if date_str:
                try:
                    date_obj = datetime.strptime(date_str, "%m/%d/%Y")
                except ValueError:
                    pass
            
            days_found.append({
                "day_name": day_name,
                "display_name": day_name.capitalize(),
                "date": date_str,
                "date_obj": date_obj,
                "data": day_data,
            })
    
    # Sort by date object (None values go to end)
    days_found.sort(key=lambda x: x["date_obj"] if x["date_obj"] else datetime.max)
    
    # Remove the date_obj from the output (it was only for sorting)
    for day in days_found:
        del day["date_obj"]
    
    return days_found


# Color scheme for day columns (left to right)
DAY_COLUMN_COLORS = [
    "#c3ddd6",  # Teal/green - first column
    "#f6cac9",  # Pink/red - second column
    "#d1c3d5",  # Purple - third column
    "#fcf7d2",  # Yellow - fourth column (if needed)
    "#d5e0ec",  # Blue - fifth column (if needed)
    "#e8d5c3",  # Tan - sixth column (if needed)
    "#c3e8d5",  # Light green - seventh column (if needed)
]


def get_day_color(index: int) -> str:
    """
    Get the background color for a day column by its index.
    
    Args:
        index: 0-based index of the day column
        
    Returns:
        Hex color string for the background
    """
    return DAY_COLUMN_COLORS[index % len(DAY_COLUMN_COLORS)]
