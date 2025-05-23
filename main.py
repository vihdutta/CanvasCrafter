import uuid
import os
from fastapi import FastAPI, Request, UploadFile, File, HTTPException, status, Cookie, Response
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from files.backend.build_html import build_from_upload
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
async def upload_file(
    response: Response,
    file: UploadFile = File(...)
):
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

    unique_filename = build_from_upload(file, uuid, UPLOAD_DIR, contents)

    # returns identifier for the folder created that contains the week files
    # if the user chooses to download the html files, then the cookie will
    # be used to determine which folder on the server to serve back and delete
    response.set_cookie(
        key="last_uploaded_file_identifier",
        value=os.path.basename(unique_filename),
        max_age=3600,
        httponly=True,
        samesite="lax"
    )

    return {"filename": unique_filename, "url": f"/uploads/{unique_filename}"}


def allowed_file(filename: str) -> bool:
    return filename.lower().endswith((".xlsx", ".xls"))
