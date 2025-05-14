from dataclasses import dataclass
from datetime import date

@dataclass
class Day:
    prework: str
    referenced_reading: str

# in main, create an array of Week classes to represent the data for each week's HTML page
@dataclass
class Week:
    # general information
    number: int
    module: int
    dates: list[date] # from the date, you can figure out the day of the week
    assigned: str
    due: str

    # overview section (need to think about the schedule info and upcoming work)
    overview_statement: str

    # learning objectives section (add image variable?)
    learning_objectives: list[str]

    # week activities section
    days: list[Day]

    # course information (shared info between all Weeks)
    course_information: str = None
    full_schedule_calendar: str = None
    canvas_modules: str = None
    course_syllabus: str = None
    instructors_and_office_hours: str = None
