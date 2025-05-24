from datetime import datetime
import pandas as pd
import yaml
import numpy as np


# populates the Week objects from the yaml and excel schedule files
def populate_weeks(
    excel_schedule_path: str,
    overview_path: str,
    objectives_path: str,
    images_path: str
):
    DATA_START_ROW = 1
    df = pd.read_excel(excel_schedule_path, engine="openpyxl")
    weeks_column = df.iloc[DATA_START_ROW:, 1].ffill().astype(int)
    df = df.replace(np.nan, "")

    overview_data, objective_data, images_data = read_overview_and_objective_yaml(overview_path, objectives_path, images_path)

    weeks = {}
    for w in set(weeks_column):
        weeks[w] = {}
        weeks[w]["module"] = ""
        weeks[w]["overview_statement"] = overview_data[w]["description"]
        weeks[w]["image"] = images_data[w]

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

            weeks[weeks_column[index]][weekday]["date"] = formatted_date
            weeks[weeks_column[index]][weekday]["referenced"] = row[7]
            weeks[weeks_column[index]][weekday]["assigned"] = row[9]
            weeks[weeks_column[index]][weekday]["due"] = row[10]
        else:
            print(f"Warning: Row {index} has non-datetime value in date field: {row[4]}")

    for w in set(weeks_column):
        weeks[w]["learning_objectives"] = objective_data[weeks[w]["module"]]["learning_objectives"]
        weeks[w]["learning_objectives_topic"] = objective_data[weeks[w]["module"]]["learning_objectives_topic"]

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


if __name__ == "__main__":
    excel_schedule_path = "files/yaml/schedule.xlsx"
    overview_path = "files/yaml/overview_statements.yaml"
    objectives_path = "files/yaml/learning_objectives.yaml"
    images_path = "files/yaml/images.yaml"

    weekly_page_data = populate_weeks(
        excel_schedule_path=excel_schedule_path,
        overview_path=overview_path,
        objectives_path=objectives_path,
        images_path=images_path
    )
    print(weekly_page_data)