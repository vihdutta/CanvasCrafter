import os
import requests
from datetime import datetime
from typing import Dict, List
from jinja2 import Environment, FileSystemLoader
from ..checkout_utils import (
    collect_checkout_assignments,
    find_homework_due_for_checkout,
    get_collaboration_learning_objectives,
    get_communications_learning_objectives,
    format_checkout_due_date,
    generate_checkout_task_text
)


def build_checkout_html(
    weeks_data: Dict, unique_identifier: str = "checkout", course_id: str | None = None, homework_urls: Dict[str, str] = None
) -> List[str]:
    """
    Build HTML files for all checkout assignments found in the weeks data.
    
    Args:
        weeks_data: Dictionary containing all weeks data
        unique_identifier: Unique identifier for this build session
        course_id: Canvas course ID
        homework_urls: Dictionary mapping homework titles to their Canvas URLs (optional)
        
    Returns:
        List of paths to generated checkout HTML files
    """
    template_dir = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "templates"
    )
    base_temp_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "temp")
    output_dir = os.path.join(base_temp_dir, unique_identifier)

    # Create the output directory
    os.makedirs(output_dir, exist_ok=True)

    print(f"Checkout Template directory: {os.path.abspath(template_dir)}")
    print(f"Checkout Output directory: {os.path.abspath(output_dir)}")

    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("checkout_template.html")

    checkout_files = []
    
    # Get all checkouts from the weeks data
    all_checkouts = collect_checkout_assignments(weeks_data)
    
    for checkout in all_checkouts:
        # Find the homework due in the same week as this checkout
        hw_number, hw_due_date = find_homework_due_for_checkout(weeks_data, checkout["week_number"])
        
        # Format the checkout due date
        formatted_due_date = format_checkout_due_date(checkout["date"])
        
        # Generate task text with homework reference and link
        homework_url = None
        if homework_urls and hw_number:
            # Look for homework URL in the format "HW01", "HW02", etc.
            hw_title = f"HW{int(hw_number):02d}"
            homework_url = homework_urls.get(hw_title)
        
        task_text = generate_checkout_task_text(hw_number, str(checkout["checkout_number"]), homework_url)
        
        # Get learning objectives directly from YAML file using module number
        module_number = checkout["module"]  # This is just checkout_number now
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
        
        # Get collaboration and communications learning objectives
        collaboration_objectives = get_collaboration_learning_objectives()
        communications_objectives = get_communications_learning_objectives()
        
        html = template.render(
            checkout_number=checkout["checkout_number"],
            checkout_date=checkout["date"],
            formatted_due_date=formatted_due_date,
            module_number=checkout["module"],
            learning_objectives=learning_objectives,
            learning_objectives_topic=learning_objectives_topic,
            collaboration_objectives=collaboration_objectives,
            communications_objectives=communications_objectives,
            task_text=task_text,
            homework_number=hw_number,
            course_id=course_id,
        )

        # Write HTML file
        filename = f"checkout_{checkout['checkout_number']}_{unique_identifier}.html"
        output_file = os.path.join(output_dir, filename)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html)

        checkout_files.append(output_file)
        print(f"Generated checkout HTML: {filename}")

    print(f"Generated {len(checkout_files)} checkout HTML files in: {output_dir}")
    return checkout_files


def upload_checkout_assignment(
    title: str,
    html_content: str,
    course_id: str,
    access_token: str,
    due_date: str = None,
) -> Dict:
    """
    Upload a checkout to Canvas as an assignment.
    
    Args:
        title: Title of the checkout (e.g., "Checkout1")
        html_content: HTML content of the checkout
        course_id: Canvas course ID
        access_token: Canvas API access token
        due_date: Due date of the checkout in MM/DD/YYYY format
        
    Returns:
        Dictionary with success status and assignment details
    """
    try:
        # Parse due date if provided
        due_at = None
        if due_date and due_date != "TBD":
            try:
                # Parse MM/DD/YYYY format and convert to ISO 8601
                parsed_date = datetime.strptime(due_date, "%m/%d/%Y")
                # Set due time to 11:59 PM (end of day)
                due_at = parsed_date.replace(hour=23, minute=59, second=59).isoformat()
            except ValueError:
                print(f"Warning: Could not parse due date '{due_date}', skipping due date")

        # Prepare assignment data for checkout
        assignment_data = {
            "assignment[name]": title,
            "assignment[description]": html_content,
            "assignment[submission_types][]": "none",  # Checkouts are presentation-based
            "assignment[points_possible]": 10,  # Low stakes, participation-based
            "assignment[grading_type]": "points",
            "assignment[published]": True,
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

        print(f"Successfully created checkout assignment '{title}' (ID: {result.get('id')})")
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

        print(f"Failed to create checkout assignment '{title}': {error_msg}")
        return {"success": False, "error": error_msg, "title": title}
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(f"Failed to create checkout assignment '{title}': {error_msg}")
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
        access_token=None,
        lecture_info_path="files/yaml/lecture_info.yaml"
    )

    checkout_files = build_checkout_html(weekly_page_data)
    print(f"Generated checkout files: {checkout_files}")