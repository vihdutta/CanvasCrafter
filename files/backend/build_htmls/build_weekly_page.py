import os
import glob
import pickle
from jinja2 import Environment, FileSystemLoader
from files.backend.populate_weeks import populate_weeks
from files.backend.build_htmls.build_hw import build_homework_html
from files.backend.build_htmls.build_quiz import build_quiz_html
from files.backend.build_htmls.build_checkout import build_checkout_html
from files.backend.pdf_utils import fetch_course_pdfs

# Import quiz and checkout utility functions
from files.backend.populate_weeks_utils import (
    find_next_quiz,
    find_next_checkout,
    get_week_title_with_topic_and_date,
    title_to_url_safe,
    collect_homework_assignments_opening_during_week,
    collect_homework_assignments_due_during_week,
    get_week_days_in_order,
    get_day_color,
)


# builds all html files and returns list containing the built files' names
def build_html(
    weeks_data,
    unique_identifier="page",
    course_id=None,
    homework_urls=None,
    quiz_urls=None,
    checkout_urls=None,
    access_token=None,
):
    template_dir = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "templates"
    )
    base_temp_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "temp")
    output_dir = os.path.join(base_temp_dir, unique_identifier)

    # create the output directory
    os.makedirs(output_dir, exist_ok=True)

    print(f"Template directory: {os.path.abspath(template_dir)}")
    print(f"Output directory: {os.path.abspath(output_dir)}")

    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("me2024_template.html")

    # Filter out non-numeric keys (like 'icon_urls') before sorting
    keys = sorted([k for k in weeks_data.keys() if str(k).isdigit()], key=int)

    if not course_id:
        raise ValueError(
            "Course ID is required. Please set a Course ID in the Course Configuration section."
        )

    # Fetch PDF URLs for course information if access token is provided
    pdf_urls = {}
    if access_token:
        pdf_urls = fetch_course_pdfs(course_id, access_token)
        print(f"Fetched PDF URLs: {pdf_urls}")
    else:
        print("Warning: No access token provided, course PDFs will not be linked")

    for i, key in enumerate(keys):
        curr_week = weeks_data[key]

        # Artificially adjust week numbers to start at 37
        display_week_num = int(key)

        # Generate navigation links
        prev_week_num = display_week_num - 1
        next_week_num = display_week_num + 1

        # Create URL-safe slugs using the same logic as upload_to_canvas
        prev_slug = None
        next_slug = None

        if prev_week_num > 0:
            prev_week_title = get_week_title_with_topic_and_date(
                weeks_data, prev_week_num
            )
            # Convert title to URL-safe slug using the same function as everywhere else
            prev_slug = title_to_url_safe(prev_week_title)

        if i < len(keys) - 1:
            next_week_title = get_week_title_with_topic_and_date(
                weeks_data, next_week_num
            )
            # Convert title to URL-safe slug using the same function as everywhere else
            next_slug = title_to_url_safe(next_week_title)

        # Generate navigation text with links using new title format
        if prev_slug:
            last_week_text = f'<a href="https://umich.instructure.com/courses/{course_id}/pages/{prev_slug}">{prev_week_title}</a>'
        else:
            last_week_text = "N/A"

        if next_slug:
            next_week_text = f'<a href="https://umich.instructure.com/courses/{course_id}/pages/{next_slug}">{next_week_title}</a>'
        else:
            next_week_text = "N/A"

        # Find next upcoming quiz for this week
        next_quiz = find_next_quiz(weeks_data, int(key))

        # Find next upcoming checkout for this week
        next_checkout = find_next_checkout(weeks_data, int(key))

        # Collect homework assignments for this week
        homework_opening_this_week = collect_homework_assignments_opening_during_week(
            weeks_data, int(key)
        )
        homework_due_this_week = collect_homework_assignments_due_during_week(
            weeks_data, int(key)
        )

        # Get the days present in this week (dynamically from spreadsheet data)
        week_days = get_week_days_in_order(curr_week)
        # Add color to each day based on its position
        for idx, day in enumerate(week_days):
            day["color"] = get_day_color(idx)

        html = template.render(
            week=curr_week,
            week_number=display_week_num,
            last_week_text=last_week_text,
            next_week_text=next_week_text,
            course_id=course_id,
            homework_urls=homework_urls or {},
            quiz_urls=quiz_urls or {},  # Add quiz URLs
            checkout_urls=checkout_urls or {},  # Add checkout URLs
            next_quiz=next_quiz,  # Add quiz information
            next_checkout=next_checkout,  # Add checkout information
            homework_opening_this_week=homework_opening_this_week,  # Homework assignments opening this week
            homework_due_this_week=homework_due_this_week,  # Homework assignments due this week
            icon_urls=weeks_data.get("icon_urls", {}),  # Add icon URLs
            lecture_info=weeks_data.get("lecture_info", {}),  # Add lecture info
            pdf_urls=pdf_urls,  # Add PDF URLs for course information
            week_days=week_days,  # Dynamic days from spreadsheet
        )

        # write each HTML file to the unique output subdirectory
        filename = f"week_{display_week_num}_{unique_identifier}.html"
        output_file = os.path.join(output_dir, filename)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html)

    print(f"Rendered HTML files for all weeks in: {output_dir}")


def regenerate_weekly_pages_with_homework_urls(
    temp_dir,
    homework_urls,
    course_id,
    quiz_urls=None,
    checkout_urls=None,
    access_token=None,
):
    """
    Regenerate weekly pages with homework URLs and quiz URLs for proper linking.
    This function is called after homework assignments and quizzes are uploaded to Canvas.
    """

    # Look for a saved weeks_data file or reconstruct from existing files
    weeks_data_file = os.path.join(temp_dir, "weeks_data.pkl")

    if os.path.exists(weeks_data_file):
        # Load the saved weeks data
        with open(weeks_data_file, "rb") as f:
            weeks_data = pickle.load(f)
    else:
        # If no saved data, we need to extract the unique identifier and regenerate
        # Find any existing weekly file to extract the unique identifier
        weekly_files = glob.glob(os.path.join(temp_dir, "week_*.html"))
        if not weekly_files:
            raise Exception("No weekly files found to extract identifier")

        # Extract unique identifier from filename
        filename = os.path.basename(weekly_files[0])
        # Format: week_1_<unique_identifier>.html
        parts = filename.split("_")
        if len(parts) >= 3:
            unique_identifier = "_".join(parts[2:]).replace(".html", "")
        else:
            raise Exception("Could not extract unique identifier from filename")

        # We'll need to regenerate from scratch - this is a fallback
        # For now, let's use the existing approach but this is not ideal
        raise Exception("Cannot regenerate without original weeks data")

    # Extract unique identifier from temp_dir path
    unique_identifier = os.path.basename(temp_dir)

    # Regenerate weekly pages with homework URLs and quiz URLs
    build_html(
        weeks_data,
        unique_identifier,
        course_id,
        homework_urls,
        quiz_urls,
        checkout_urls,
        access_token,
    )

    # Return list of regenerated weekly files
    return glob.glob(os.path.join(temp_dir, "week_*.html"))


# builds the html files from the upload,
def build_from_upload(
    file,
    uuid_module,
    upload_dir: str,
    contents: bytes,
    course_id: str = None,
    access_token: str = None,
) -> str:
    ext = os.path.splitext(file.filename)[1].lower()
    unique_identifier = uuid_module.uuid4().hex
    unique_filename = f"{unique_identifier}{ext}"
    dest_path = os.path.join(upload_dir, unique_filename)

    os.makedirs(upload_dir, exist_ok=True)
    with open(dest_path, "wb") as out:
        out.write(contents)

    excel_schedule_path = f"uploads/{unique_filename}"
    overview_path = "files/yaml/overview_statements.yaml"
    objectives_path = "files/yaml/learning_objectives.yaml"
    images_path = "files/yaml/images.yaml"

    weekly_page_data = populate_weeks(
        excel_schedule_path=excel_schedule_path,
        overview_path=overview_path,
        objectives_path=objectives_path,
        images_path=images_path,
        course_id=course_id,
        access_token=access_token,
        lecture_info_path="files/yaml/lecture_info.yaml",
    )

    # Save the weeks data for later use in regeneration
    temp_dir = os.path.join("temp", unique_identifier)
    os.makedirs(temp_dir, exist_ok=True)
    weeks_data_file = os.path.join(temp_dir, "weeks_data.pkl")
    with open(weeks_data_file, "wb") as f:
        pickle.dump(weekly_page_data, f)

    build_html(
        weekly_page_data, unique_identifier, course_id, access_token=access_token
    )
    build_homework_html(weekly_page_data, unique_identifier, course_id, access_token)
    build_quiz_html(weekly_page_data, unique_identifier, course_id)  # Add quiz building
    build_checkout_html(
        weekly_page_data, unique_identifier, course_id
    )  # Add checkout building (no homework URLs yet)

    os.remove(excel_schedule_path)

    return unique_filename


if __name__ == "__main__":
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
        lecture_info_path="files/yaml/lecture_info.yaml",
    )

    # Example usage - replace with actual course_id when using
    # build_html(weekly_page_data, course_id="YOUR_COURSE_ID", access_token=None)
    # build_homework_html(weekly_page_data, course_id="YOUR_COURSE_ID", access_token=None)
    # build_checkout_html(weekly_page_data, course_id="YOUR_COURSE_ID")
