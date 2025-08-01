import os
import re
import requests
from datetime import datetime
from typing import Dict, List, Optional
from jinja2 import Environment, FileSystemLoader
from files.backend.populate_weeks_utils import collect_quiz_dates
from ..quiz_utils import (
    get_lesson_range_for_module,
    get_homework_range_for_module,
    format_quiz_date_time
)


def build_quiz_html(
    weeks_data: Dict, unique_identifier: str = "quiz", course_id: str | None = None
) -> List[str]:
    """
    Build HTML files for all quizzes found in the weeks data.
    
    Args:
        weeks_data: Dictionary containing all weeks data
        unique_identifier: Unique identifier for this build session
        course_id: Canvas course ID
        
    Returns:
        List of paths to generated quiz HTML files
    """
    template_dir = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "templates"
    )
    base_temp_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "temp")
    output_dir = os.path.join(base_temp_dir, unique_identifier)

    # Create the output directory
    os.makedirs(output_dir, exist_ok=True)

    print(f"Quiz Template directory: {os.path.abspath(template_dir)}")
    print(f"Quiz Output directory: {os.path.abspath(output_dir)}")

    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("quiz_template.html")

    quiz_files = []
    
    # Get all quizzes from the weeks data
    all_quizzes = collect_quiz_dates(weeks_data)
    
    for quiz in all_quizzes:
        # Get the week data for this quiz
        week_data = weeks_data.get(quiz["week_number"], {})
        
        # Get the specific day data for this quiz
        day_data = week_data.get(quiz["day"], {})
        quiz_info = day_data.get("quiz_info", {})
        
        # Extract quiz topic from the day's topic field
        topic = day_data.get("topic", "")
        quiz_topic = topic.replace(f"QUIZ {quiz['quiz_number']} & ", "")
        
        # Quiz N should test Module N content (Quiz 1 -> Module 1, Quiz 2 -> Module 2, etc.)
        module_number = quiz["quiz_number"]
        
        # Get lesson and homework ranges for this module
        lesson_range = get_lesson_range_for_module(weeks_data, module_number)
        homework_range = get_homework_range_for_module(weeks_data, module_number)
        
        # Format the quiz date
        formatted_quiz_date, day_of_week = format_quiz_date_time(quiz["date"])
        
        # Get learning objectives for the correct module
        # We need to load the objectives data to get the right module's objectives
        try:
            import yaml
            objectives_path = "files/yaml/learning_objectives.yaml"
            with open(objectives_path, "r", encoding="utf-8") as f:
                objective_data = yaml.safe_load(f)
            
            module_objectives = objective_data.get(module_number, {})
            learning_objectives = module_objectives.get("learning_objectives", [])
            learning_objectives_topic = module_objectives.get("learning_objectives_topic", "General")
        except Exception as e:
            print(f"Warning: Could not load learning objectives for module {module_number}: {e}")
            learning_objectives = []
            learning_objectives_topic = "General"
        
        html = template.render(
            quiz_number=quiz["quiz_number"],
            quiz_date=quiz["date"],
            formatted_quiz_date=formatted_quiz_date,
            quiz_topic=quiz_topic,
            module_number=module_number,
            lesson_range=lesson_range,
            homework_range=homework_range,
            learning_objectives=learning_objectives,
            learning_objectives_topic=learning_objectives_topic,
            sample_quiz_url=quiz_info.get("sample_quiz_url", ""),
            course_id=course_id,
        )

        # Write HTML file
        filename = f"quiz_{quiz['quiz_number']}_{unique_identifier}.html"
        output_file = os.path.join(output_dir, filename)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html)

        quiz_files.append(output_file)
        print(f"Generated quiz HTML: {filename}")

    return quiz_files


def upload_quiz_assignment(
    title: str,
    html_content: str,
    course_id: str,
    access_token: str,
    quiz_date: str = None,
) -> Dict:
    """
    Upload a quiz to Canvas as an assignment.
    
    Args:
        title: Title of the quiz (e.g., "Quiz 1")
        html_content: HTML content of the quiz
        course_id: Canvas course ID
        access_token: Canvas API access token
        quiz_date: Date of the quiz in MM/DD/YYYY format
        
    Returns:
        Dictionary with success status and assignment details
    """
    try:
        # Parse quiz date if provided
        due_at = None
        if quiz_date:
            try:
                # Parse MM/DD/YYYY format and convert to ISO 8601
                parsed_date = datetime.strptime(quiz_date, "%m/%d/%Y")
                # Set due time to the beginning of class (11:30 AM)
                due_at = parsed_date.replace(hour=11, minute=30, second=0).isoformat()
            except ValueError:
                print(f"Warning: Could not parse quiz date '{quiz_date}', skipping due date")

        # Prepare assignment data for quiz (same structure as homework)
        assignment_data = {
            "assignment[name]": title,
            "assignment[description]": html_content,
            "assignment[submission_types][]": "online_upload",  # Same as homework
            "assignment[points_possible]": 25,  # Standard quiz points
            "assignment[grading_type]": "points",
            "assignment[published]": True,  # Published like homework
            "assignment[allowed_extensions][]": "pdf",  # Same as homework
        }

        if due_at:
            assignment_data["assignment[due_at]"] = due_at

        # Create the assignment
        response = requests.post(
            f"https://umich.instructure.com/api/v1/courses/{course_id}/assignments",
            headers={"Authorization": f"Bearer {access_token}"},
            data=assignment_data,
        )

        response.raise_for_status()
        result = response.json()

        print(f"Successfully created assignment '{title}' (ID: {result.get('id')})")
        return {
            "success": True,
            "assignment_id": result.get("id"),
            "title": title,
            "url": result.get("html_url"),
            "due_at": result.get("due_at"),
        }

    except requests.exceptions.RequestException as e:
        error_msg = f"Canvas API error: {str(e)}"
        if hasattr(e, "response") and e.response is not None:
            try:
                error_detail = e.response.json()
                error_msg = f"Canvas API error: {error_detail}"
            except:
                error_msg = (
                    f"Canvas API error: {e.response.status_code} - {e.response.text}"
                )

        print(f"Failed to create quiz assignment '{title}': {error_msg}")
        return {"success": False, "error": error_msg, "title": title}
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(f"Failed to create quiz assignment '{title}': {error_msg}")
        return {"success": False, "error": error_msg, "title": title}


# Test function for development
if __name__ == "__main__":
    from files.backend.populate_weeks import populate_weeks
    
    excel_schedule_path = "files/yaml/schedule.xlsx"
    overview_path = "files/yaml/overview_statements.yaml"
    objectives_path = "files/yaml/learning_objectives.yaml"
    images_path = "files/yaml/images.yaml"

    weekly_page_data = populate_weeks(
        excel_schedule_path=excel_schedule_path,
        overview_path=overview_path,
        objectives_path=objectives_path,
        images_path=images_path,
        course_id=None,  # Canvas credentials not available in direct script run
        access_token=None
    )

    quiz_files = build_quiz_html(weekly_page_data)
    print(f"Generated quiz files: {quiz_files}") 