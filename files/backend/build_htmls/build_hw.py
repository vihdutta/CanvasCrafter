import os
import re
import requests
from datetime import datetime
from typing import Dict, List
from jinja2 import Environment, FileSystemLoader
from files.backend.populate_weeks import populate_weeks


def build_homework_html(
    weeks_data: Dict, unique_identifier: str = "hw", course_id: str | None = None
) -> List[str]:
    template_dir = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "templates"
    )
    base_temp_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "temp")
    output_dir = os.path.join(base_temp_dir, unique_identifier)

    # Create the output directory
    os.makedirs(output_dir, exist_ok=True)

    print(f"Homework Template directory: {os.path.abspath(template_dir)}")
    print(f"Homework Output directory: {os.path.abspath(output_dir)}")

    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("homework_template.html")

    homework_files = []

    # Process each week to find homework assignments
    for week_num, week_data in weeks_data.items():
        homework_assignments = []

        # Check each day of the week for assignments or due dates
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

                if (
                    "assigned" in day_data
                    and day_data["assigned"]
                    and "HW" in str(day_data["assigned"]).upper()
                ):
                    hw_number = extract_homework_number(day_data["assigned"])
                    if hw_number:
                        due_date = find_homework_due_date(weeks_data, hw_number)

                        homework_assignments.append(
                            {
                                "number": hw_number,
                                "assigned_date": day_data["date"],
                                "due_date": due_date,
                                "module": week_data.get("module", 1),
                                "learning_objectives": week_data.get(
                                    "learning_objectives", []
                                ),
                                "learning_objectives_topic": week_data.get(
                                    "learning_objectives_topic", "General"
                                ),
                            }
                        )

        # Generate HTML for each homework assignment found in this week
        for hw in homework_assignments:
            html = template.render(
                homework_number=hw["number"],
                assigned_date=hw["assigned_date"],
                due_date=hw["due_date"],
                module_number=hw["module"],
                learning_objectives=hw["learning_objectives"],
                learning_objectives_topic=hw["learning_objectives_topic"],
                course_id=course_id,
            )

            # Write HTML file
            filename = f"homework_{hw['number']}_{unique_identifier}.html"
            output_file = os.path.join(output_dir, filename)
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(html)

            homework_files.append(output_file)
            print(f"Generated homework HTML: {filename}")

    print(f"Generated {len(homework_files)} homework HTML files in: {output_dir}")
    return homework_files


def extract_homework_number(assignment_text: str) -> str:
    """Extract homework number from assignment text like 'HW1', 'HW 2', 'Homework 3', etc."""
    if not assignment_text:
        return None

    # Look for patterns like HW1, HW 2, Homework 3, etc.
    patterns = [r"HW\s*(\d+)", r"Homework\s*(\d+)", r"Assignment\s*(\d+)"]

    for pattern in patterns:
        match = re.search(pattern, assignment_text, re.IGNORECASE)
        if match:
            return match.group(1)

    return None


def find_homework_due_date(weeks_data: Dict, hw_number: str) -> str:
    """Find the due date for a specific homework number across all weeks."""
    for week_num, week_data in weeks_data.items():
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


def upload_homework_assignment(
    title: str,
    html_content: str,
    course_id: str,
    access_token: str,
    due_date: str = None,
) -> Dict:
    try:
        due_at = None
        if due_date and due_date != "TBD":
            try:
                # Parse MM/DD/YYYY format and convert to ISO 8601
                parsed_date = datetime.strptime(due_date, "%m/%d/%Y")
                # Set due time to 11:59 PM
                due_at = parsed_date.replace(hour=23, minute=59, second=59).isoformat()
            except ValueError:
                print(
                    f"Warning: Could not parse due date '{due_date}', skipping due date"
                )

        # Prepare assignment data
        assignment_data = {
            "assignment[name]": title,
            "assignment[description]": html_content,
            "assignment[submission_types][]": "online_upload",
            "assignment[points_possible]": 100,
            "assignment[grading_type]": "points",
            "assignment[published]": True,
            "assignment[allowed_extensions][]": "pdf",
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

        print(f"Failed to create assignment '{title}': {error_msg}")
        return {"success": False, "error": error_msg, "title": title}
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(f"Failed to create assignment '{title}': {error_msg}")
        return {"success": False, "error": error_msg, "title": title}


if __name__ == "__main__":
    # Test with sample data
    excel_schedule_path = "files/yaml/schedule.xlsx"
    overview_path = "files/yaml/overview_statements.yaml"
    objectives_path = "files/yaml/learning_objectives.yaml"
    images_path = "files/yaml/images.yaml"

    weekly_page_data = populate_weeks(
        excel_schedule_path=excel_schedule_path,
        overview_path=overview_path,
        objectives_path=objectives_path,
        images_path=images_path,
    )

    homework_files = build_homework_html(weekly_page_data)
    print(f"Generated homework files: {homework_files}")
