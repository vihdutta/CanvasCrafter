import os
from typing import List
from jinja2 import Environment, FileSystemLoader

# dynamic import of populate_weeks based on execution context
if __name__ == '__main__':
    from populate_weeks import populate_weeks
else:
    from files.backend.populate_weeks import populate_weeks

# builds all html files and returns list containing the built files' names
def build_html(weeks_data, unique_identifier="page"):
    template_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'templates')
    base_temp_dir = os.path.join(os.path.dirname(__file__), "..", "..", "temp")
    output_dir = os.path.join(base_temp_dir, unique_identifier)

    # create the output directory
    os.makedirs(output_dir, exist_ok=True)

    print(f"Template directory: {os.path.abspath(template_dir)}")
    print(f"Output directory: {os.path.abspath(output_dir)}")

    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template('me2024_template.html')

    keys = sorted(weeks_data.keys(), key=int)
    for key in keys:
        curr_week = weeks_data[key]

        html = template.render(
            week=curr_week,
            week_number=key
        )

        # write each HTML file to the unique output subdirectory
        filename = f"week_{key}_{unique_identifier}.html"
        output_file = os.path.join(output_dir, filename)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)

    print(f"Rendered HTML files for all weeks in: {output_dir}")

# builds the html files from the upload, returns the file_name that was created.
def build_from_upload(file, uuid, UPLOAD_DIR, contents) -> str:
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

    weekly_page_data = populate_weeks(
        excel_schedule_path=excel_schedule_path,
        overview_path=overview_path,
        objectives_path=objectives_path
    )

    build_html(weekly_page_data, unique_identifier=unique_identifier)
    os.remove(excel_schedule_path)

    return unique_filename

if __name__ == "__main__":
    excel_schedule_path = "files/yaml/schedule.xlsx"
    overview_path = "files/yaml/overview_statements.yaml"
    objectives_path = "files/yaml/learning_objectives.yaml"

    weekly_page_data = populate_weeks(
        excel_schedule_path=excel_schedule_path,
        overview_path=overview_path,
        objectives_path=objectives_path
    )

    build_html(weekly_page_data)