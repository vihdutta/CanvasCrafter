from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from datetime import datetime, timedelta
from files.classes.week import Week

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# add custom Jinja2 filters
templates.env.filters["add_days"] = lambda value, days: value + timedelta(days=days)
templates.env.filters["strftime"] = lambda value, fmt: value.strftime(fmt)

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    today = datetime.today()
    context = {
        "request": request,
        "week_number": 5,
        "week_start": today,
        "last_week_text": "last_week_text",
        "next_week_text": "next_week_text",
        "full_course_schedule_text": "See the Full Course Schedule",
        "module_number": 3,
        "module_number_learning_objectives": "Understand FastAPI & Jinja integration"
    }
    
    return {templates.TemplateResponse("index.html", context)}
