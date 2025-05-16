import os
import uuid
import shutil
from fastapi import FastAPI, Request, UploadFile, File, HTTPException, status
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from files.backend.populate_weeks import populate_weeks

app = FastAPI()
templates = Jinja2Templates(directory="templates")

UPLOAD_DIR = "uploads"
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@app.get("/")
async def root(request: Request):
    # weeks = populate_weeks("files/yaml/schedule.xlsx", "files/yaml/overview_statements.yaml", "files/yaml/learning_objectives.yaml")
    # return {"message": weeks}
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api")
async def api():
    weekly_page_data = populate_weeks(
        "files/yaml/schedule.xlsx",
        "files/yaml/overview_statements.yaml",
        "files/yaml/learning_objectives.yaml",
    )
    return {"message": weekly_page_data}


# helper functions, not sites


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not allowed_file(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .xlsx/.xls files are allowed",
        )

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large (max {MAX_FILE_SIZE // (1024 * 1024)} MB)",
        )

    ext = os.path.splitext(file.filename)[1].lower()
    unique_name = f"{uuid.uuid4().hex}{ext}"
    dest_path = os.path.join(UPLOAD_DIR, unique_name)

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    with open(dest_path, "wb") as out:
        out.write(contents)

    return {"filename": unique_name, "url": f"/uploads/{unique_name}"}


def allowed_file(filename: str) -> bool:
    return filename.lower().endswith((".xlsx", ".xls"))
