import pandas as pd
import yaml
import numpy as np


# populates the Week objects from the yaml and excel schedule files
def populate_weeks(
    excel_schedule_path: str,
    overview_path: str,
    objectives_path: str,
):
    DATA_START_ROW = 1
    df = pd.read_excel(excel_schedule_path, engine="openpyxl")
    weeks_column = df.iloc[DATA_START_ROW:, 1].ffill().astype(int)
    df = df.replace(np.nan, "")

    overview_data, objective_data = read_overview_and_objective_yaml(overview_path, objectives_path)

    weeks = {}
    for w in set(weeks_column):
        weeks[w] = {}
        weeks[w]["module"] = ""
        weeks[w]["dates"] = []
        weeks[w]["referenced"] = []
        weeks[w]["assigned"] = []
        weeks[w]["due"] = []
        weeks[w]["overview_statement"] = overview_data[w]["description"]

    for index, row in df.iterrows():
        if index == 0:
            continue
        if "Mod" not in str(weeks[weeks_column[index]]["module"]) and str(row[2]) != "":
            weeks[weeks_column[index]]["module"] = int("".join(c for c in row[2] if c.isdigit()))
        elif str(row[2]) == "":
            weeks[weeks_column[index]]["module"] = weeks[weeks_column[index - 1]]["module"]

        weeks[weeks_column[index]]["dates"].append(row[4])
        weeks[weeks_column[index]]["referenced"].append(row[7])
        weeks[weeks_column[index]]["assigned"].append(row[9])
        weeks[weeks_column[index]]["due"].append(row[10])

    for w in set(weeks_column):
        weeks[w]["learning_objectives"] = objective_data[weeks[w]["module"]]["learning_objectives"]

    return weeks

def read_overview_and_objective_yaml(
    overview_path: str,
    objectives_path: str
):
    overview_data = {}
    objective_data = {}
    if overview_path:
        with open(overview_path, "r", encoding="utf-8") as f:
            overview_data = yaml.safe_load(f)
    if objectives_path:
        with open(objectives_path, "r", encoding="utf-8") as f:
            objective_data = yaml.safe_load(f)

    return (overview_data, objective_data)


if __name__ == "__main__":
    excel_schedule_path = "files/yaml/schedule.xlsx"
    overview_path = "files/yaml/overview_statements.yaml"
    objectives_path = "files/yaml/learning_objectives.yaml"

    weekly_page_data = populate_weeks(
        excel_schedule_path=excel_schedule_path,
        overview_path=overview_path,
        objectives_path=objectives_path
    )
    print(weekly_page_data)