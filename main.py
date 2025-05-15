from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from datetime import timedelta
from files.populate_weeks.populate_weeks import populate_weeks

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# add custom Jinja2 filters
templates.env.filters["add_days"] = lambda value, days: value + timedelta(days=days)
templates.env.filters["strftime"] = lambda value, fmt: value.strftime(fmt)

@app.get("/")
async def root(request: Request):
    weeks = populate_weeks("files/yaml/schedule.xlsx", "files/yaml/overview_statements.yaml", "files/yaml/learning_objectives.yaml")
    return {"message": weeks}
    # return {templates.TemplateResponse("index.html", context)}