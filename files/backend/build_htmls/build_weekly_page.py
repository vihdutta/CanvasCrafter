import os
import re
from typing import List
from jinja2 import Environment, FileSystemLoader
from files.backend.populate_weeks import populate_weeks
from files.backend.build_htmls.build_hw import build_homework_from_weeks_data


# builds all html files and returns list containing the built files' names
def build_html(weeks_data, unique_identifier="page", course_id=None):
    template_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "templates")
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

        # Generate navigation links
        prev_week_num = int(key) - 1
        next_week_num = int(key) + 1

        # Create URL-safe slugs
        prev_slug = f"week-{prev_week_num}" if prev_week_num > 0 else None
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
            week_number=key,
            last_week_text=last_week_text,
            next_week_text=next_week_text,
        )

        # write each HTML file to the unique output subdirectory
        filename = f"week_{key}_{unique_identifier}.html"
        output_file = os.path.join(output_dir, filename)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html)

    print(f"Rendered HTML files for all weeks in: {output_dir}")


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

    build_html(
        weekly_page_data, unique_identifier=unique_identifier, course_id=course_id
    )
    build_homework_from_weeks_data(weekly_page_data, unique_identifier)

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
