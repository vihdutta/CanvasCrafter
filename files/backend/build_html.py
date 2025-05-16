import os
from jinja2 import Environment, FileSystemLoader
from populate_weeks import populate_weeks

def build_html(weeks_data):
    template_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'templates')
    temp_dir = os.path.join(os.path.dirname(__file__), "..", "..", "temp")
    print(f"Template directory: {os.path.abspath(template_dir)}")
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template('me2024_template.html')

    keys = sorted(weeks_data.keys(), key=int)
    for key in keys:
        curr_week = weeks_data[key]

        html = template.render(
            week=curr_week,
        )

        # write each HTML file to the temp directory
        output_file = os.path.join(temp_dir, f'week_{key}.html')
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)

    print(f"Rendered HTML files for all weeks in temp directory: {temp_dir}")

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