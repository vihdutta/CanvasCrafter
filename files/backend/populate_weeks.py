from datetime import datetime
import pandas as pd
import yaml
import numpy as np

# Import utility functions from the new utils module
from files.backend.populate_weeks_utils import (
    title_to_url_safe,
    fetch_canvas_pages,
    process_quiz_from_topic,
    process_checkout_from_topic,
)
from files.backend.get_image_urls import get_image_urls_for_yaml_data


# populates the Week objects from the yaml and excel schedule files
def populate_weeks(
    excel_schedule_path: str,
    overview_path: str,
    objectives_path: str,
    images_path: str,
    course_id: str = None,
    access_token: str = None,
    lecture_info_path: str = "files/yaml/lecture_info.yaml"
):
    DATA_START_ROW = 1
    df = pd.read_excel(excel_schedule_path, engine="openpyxl")
    weeks_column = df.iloc[DATA_START_ROW:, 1].ffill().astype(int)
    df = df.replace(np.nan, "")

    overview_data, objective_data, images_data = read_overview_and_objective_yaml(overview_path, objectives_path, images_path)
    lecture_info = load_lecture_info(lecture_info_path)

    image_urls, icon_urls = get_image_urls_for_yaml_data(images_data, course_id, access_token)

    sample_quiz_urls = {}
    if course_id and access_token:
        print("Fetching sample quiz pages from Canvas...")
        sample_quiz_urls = fetch_canvas_pages(course_id, access_token)
        print(f"Found {len(sample_quiz_urls)} sample quiz pages")

    weeks = {}
    for w in set(weeks_column):
        weeks[w] = {}
        weeks[w]["module"] = ""
        weeks[w]["overview_statement"] = overview_data[w]["description"]
        weeks[w]["image"] = image_urls[w]

    for index, row in df.iterrows():
        if index == 0:
            continue

        # handle module assignment for the week:
        # if the current row contains a module number, assign it.
        # otherwise, inherit the module from the previous week.
        if "Mod" not in str(weeks[weeks_column[index]]["module"]) and str(row[2]) != "":
            weeks[weeks_column[index]]["module"] = int("".join(c for c in row[2] if c.isdigit()))
        elif str(row[2]) == "":
            weeks[weeks_column[index]]["module"] = weeks[weeks_column[index - 1]]["module"]

        # format the date from the excel file to MM/DD/YYYY
        if isinstance(row[4], pd.Timestamp) or isinstance(row[4], datetime):
            date_obj = row[4]
            formatted_date = date_obj.strftime("%m/%d/%Y")
            weekday_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            weekday = weekday_names[date_obj.weekday()]  # ex: "monday"

            if weekday not in weeks[weeks_column[index]]:
                weeks[weeks_column[index]][weekday] = {}

            weeks[weeks_column[index]][weekday]["lesson"] = row[3]
            weeks[weeks_column[index]][weekday]["date"] = formatted_date
            weeks[weeks_column[index]][weekday]["topic"] = row[6]
            weeks[weeks_column[index]][weekday]["referenced"] = row[7]
            weeks[weeks_column[index]][weekday]["assigned"] = row[8]
            weeks[weeks_column[index]][weekday]["due"] = row[9]
            
            quiz_info = process_quiz_from_topic(row[6], sample_quiz_urls)
            weeks[weeks_column[index]][weekday]["quiz_info"] = quiz_info
            checkout_info = process_checkout_from_topic(row[6])
            weeks[weeks_column[index]][weekday]["checkout_info"] = checkout_info
            
            prework_title_raw = str(row[11]).strip() if not pd.isna(row[11]) else ""
            if prework_title_raw and prework_title_raw != "":
                current_module = weeks[weeks_column[index]]["module"]
                prework_title_with_prefix = f"Prework Module {current_module} - {prework_title_raw}"
                weeks[weeks_column[index]][weekday]["prework_video_title"] = prework_title_with_prefix
                url_safe_title = title_to_url_safe(prework_title_with_prefix)
                if url_safe_title and course_id:
                    prework_link = f"https://umich.instructure.com/courses/{course_id}/pages/{url_safe_title}"
                    weeks[weeks_column[index]][weekday]["prework_video_link"] = prework_link
                else:
                    weeks[weeks_column[index]][weekday]["prework_video_link"] = ""
            else:
                weeks[weeks_column[index]][weekday]["prework_video_title"] = row[11]
                weeks[weeks_column[index]][weekday]["prework_video_link"] = ""

        else:
            print(f"Warning: Row {index} has non-datetime value in date field: {row[4]}")

    for w in set(weeks_column):
        weeks[w]["learning_objectives"] = objective_data[weeks[w]["module"]]["learning_objectives"]
        weeks[w]["learning_objectives_topic"] = objective_data[weeks[w]["module"]]["learning_objectives_topic"]

    # Add icon URLs to the returned data structure
    weeks["icon_urls"] = icon_urls
    
    # Add lecture info to the returned data structure
    weeks["lecture_info"] = lecture_info
    
    return weeks

def read_overview_and_objective_yaml(
    overview_path: str,
    objectives_path: str,
    images_path: str
):
    overview_data = {}
    objective_data = {}
    images_data = {}

    with open(overview_path, "r", encoding="utf-8") as f:
        overview_data = yaml.safe_load(f)
    with open(objectives_path, "r", encoding="utf-8") as f:
        objective_data = yaml.safe_load(f)
    with open(images_path, "r", encoding="utf-8") as f:
        images_data = yaml.safe_load(f)

    return (overview_data, objective_data, images_data)


def load_lecture_info(lecture_info_path: str = "files/yaml/lecture_info.yaml"):
    """Load lecture information from YAML file."""
    with open(lecture_info_path, "r", encoding="utf-8") as f:
        lecture_info = yaml.safe_load(f)
    return lecture_info


def get_lecture_days_list(lecture_info_path: str = "files/yaml/lecture_info.yaml"):
    """
    Get list of lecture days in lowercase from YAML file.
    Default: ['monday', 'wednesday', 'friday']
    """
    try:
        lecture_info = load_lecture_info(lecture_info_path)
        days_string = lecture_info.get("lecture_days", "Monday, Wednesday, & Friday")
        
        # Parse the days string to extract individual days
        # Remove common separators and convert to lowercase
        days_string = days_string.replace("&", ",").replace(" and ", ",")
        days = [day.strip().lower() for day in days_string.split(",") if day.strip()]
        
        return days
    except Exception as e:
        print(f"Warning: Could not load lecture days from {lecture_info_path}: {e}")
        # Default fallback
        return ["monday", "wednesday", "friday"]


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
        lecture_info_path="files/yaml/lecture_info.yaml"
    )
    print(weekly_page_data)