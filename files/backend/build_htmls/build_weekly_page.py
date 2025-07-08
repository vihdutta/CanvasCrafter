import os
import re
import glob
import pickle
from typing import List
from jinja2 import Environment, FileSystemLoader
from files.backend.populate_weeks import populate_weeks
from files.backend.build_htmls.build_hw import build_homework_html


# builds all html files and returns list containing the built files' names
def build_html(weeks_data, unique_identifier="page", course_id=None, homework_urls=None):
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

    keys = sorted(weeks_data.keys(), key=int)

    if not course_id:
        raise ValueError(
            "Course ID is required. Please set a Course ID in the Course Configuration section."
        )

    for i, key in enumerate(keys):
        curr_week = weeks_data[key]

        # Artificially adjust week numbers to start at 17
        display_week_num = int(key) + 100  # This makes week 1 become week 17

        # Generate navigation links
        prev_week_num = display_week_num - 1
        next_week_num = display_week_num + 1

        # Create URL-safe slugs
        prev_slug = f"week-{prev_week_num}" if prev_week_num > 100 else None
        next_slug = f"week-{next_week_num}" if i < len(keys) - 1 else None

        # Generate navigation text with links
        if prev_slug:
            last_week_text = f'<a href="https://umich.instructure.com/courses/{course_id}/pages/{prev_slug}">Week {prev_week_num}</a>'
        else:
            last_week_text = "N/A"

        if next_slug:
            next_week_text = f'<a href="https://umich.instructure.com/courses/{course_id}/pages/{next_slug}">Week {next_week_num}</a>'
        else:
            next_week_text = "N/A"

        html = template.render(
            week=curr_week,
            week_number=display_week_num,
            last_week_text=last_week_text,
            next_week_text=next_week_text,
            course_id=course_id,
            homework_urls=homework_urls or {},
        )

        # write each HTML file to the unique output subdirectory
        filename = f"week_{display_week_num}_{unique_identifier}.html"
        output_file = os.path.join(output_dir, filename)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html)

    print(f"Rendered HTML files for all weeks in: {output_dir}")

def regenerate_weekly_pages_with_homework_urls(temp_dir, homework_urls, course_id):
    """
    Regenerate weekly pages with homework URLs for proper linking.
    This function is called after homework assignments are uploaded to Canvas.
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
    
    # Regenerate weekly pages with homework URLs
    build_html(weeks_data, unique_identifier, course_id, homework_urls)
    
    # Return list of regenerated weekly files
    return glob.glob(os.path.join(temp_dir, "week_*.html"))


# builds the html files from the upload, returns the file_name that was created.
def build_from_upload(
    file, uuid, UPLOAD_DIR, contents, course_id=None, access_token=None
) -> str:
    ext = os.path.splitext(file.filename)[1].lower()
    unique_identifier = uuid.uuid4().hex
    unique_filename = f"{unique_identifier}{ext}"
    dest_path = os.path.join(UPLOAD_DIR, unique_filename)

    os.makedirs(UPLOAD_DIR, exist_ok=True)
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
    )

    # Save the weeks data for later use in regeneration
    temp_dir = os.path.join("temp", unique_identifier)
    os.makedirs(temp_dir, exist_ok=True)
    weeks_data_file = os.path.join(temp_dir, "weeks_data.pkl")
    with open(weeks_data_file, "wb") as f:
        pickle.dump(weekly_page_data, f)
    
    build_html(weekly_page_data, unique_identifier, course_id)
    build_homework_html(weekly_page_data, unique_identifier, course_id)

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
    )

    build_html(weekly_page_data, course_id=123456)
    build_homework_html(weekly_page_data, course_id=123456)
