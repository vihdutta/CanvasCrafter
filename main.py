from typing import List
import uuid
import os
import glob
import json
from fastapi import (
    FastAPI,
    Request,
    UploadFile,
    File,
    HTTPException,
    status,
    Cookie,
    Response,
)
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from files.backend.build_htmls.build_weekly_page import build_from_upload
from files.backend.populate_weeks import populate_weeks
from files.backend.upload_to_canvas import upload_page
from files.backend.zip_built_htmls import zip_stream
from files.backend.build_htmls.build_hw import upload_homework_assignment

app = FastAPI()
templates = Jinja2Templates(directory="templates")

UPLOAD_DIR = "uploads"
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api")
async def api():
    weekly_page_data = populate_weeks(
        "files/yaml/schedule.xlsx",
        "files/yaml/overview_statements.yaml",
        "files/yaml/learning_objectives.yaml",
        "files/yaml/images.yaml",
    )
    return {"message": weekly_page_data}


# helper functions, not pages


# handles the excel file being uploaded to the server and building the HTML files automatically
@app.post("/upload")
async def upload_file(
    response: Response,
    file: UploadFile = File(...),
    course_id: str = Cookie(None),
    access_token: str = Cookie(None),
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

    unique_filename = build_from_upload(
        file, uuid, UPLOAD_DIR, contents, course_id, access_token
    )

    # returns identifier for the folder created that contains the week files
    # if the user chooses to download the html files, then the cookie will
    # be used to determine which folder on the server to serve back and delete
    response.set_cookie(
        key="file_group_identifier",
        value=os.path.splitext(unique_filename)[0],
        max_age=3600,
        httponly=True,
        samesite="lax",
    )

    return {"filename": unique_filename, "url": f"/uploads/{unique_filename}"}


def allowed_file(filename: str) -> bool:
    return filename.lower().endswith((".xlsx", ".xls"))


# when "Generate Pages" is pressed, preview each of the generated pages.
@app.get("/generate")
async def generate(path: str):
    try:
        # the unique identifier == the filename (without extension)
        filename = os.path.basename(path)
        unique_identifier = os.path.splitext(filename)[0]

        # find the generated HTML files folder
        temp_dir = os.path.join("temp", unique_identifier)
        if not os.path.exists(temp_dir):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Generated files folder not found",
            )

        html_files = glob.glob(os.path.join(temp_dir, "*.html"))

        if not html_files:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="No generated files found"
            )

        # Separate weekly pages from homework files
        weekly_files = []
        homework_files = []

        for html_file in html_files:
            filename = os.path.basename(html_file)
            if filename.startswith("homework_"):
                # homework file
                hw_number = filename.split("_")[1]
                with open(html_file, "r", encoding="utf-8") as f:
                    html_content = f.read()

                homework_files.append(
                    {
                        "name": f"Homework {hw_number}",
                        "html": html_content,
                        "type": "homework",
                        "hw_number": hw_number,
                    }
                )
            elif filename.startswith("week_"):
                # weekly page file
                week_name = (
                    filename.replace(f"_{unique_identifier}.html", "")
                    .replace("_", " ")
                    .title()
                )
                with open(html_file, "r", encoding="utf-8") as f:
                    html_content = f.read()

                weekly_files.append(
                    {"name": week_name, "html": html_content, "type": "weekly"}
                )

        # Sort weekly files numerically by week number
        def get_week_number(item):
            try:
                return int(item["name"].lower().replace("week ", ""))
            except (ValueError, AttributeError):
                return float("inf")

        weekly_files = sorted(weekly_files, key=get_week_number)

        # Sort homework files numerically by homework number
        def get_hw_number(item):
            try:
                return int(item.get("hw_number", "0"))
            except (ValueError, AttributeError):
                return float("inf")

        homework_files = sorted(homework_files, key=get_hw_number)

        # Combine weekly and homework files
        all_files = weekly_files + homework_files

        return all_files

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating pages: {str(e)}",
        )


# download all generated HTML files as a zip using the cookie identifier
@app.get("/download")
async def download_all(file_group_identifier: str = Cookie(None)):
    html_files = await retrieve_generated_files(file_group_identifier)
    return zip_stream(html_files)


# uploads the generated files to canvas - now handles both weekly pages and homework in one unified upload
@app.get("/upload-to-canvas")
async def upload_to_canvas(
    file_group_identifier: str = Cookie(None),
    course_id: str = Cookie(None),
    access_token: str = Cookie(None),
):
    html_files = await retrieve_generated_files(file_group_identifier)

    # Validate course_id and access_token are provided
    if not course_id or not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Course ID and Access Token are required. Please set them in the Canvas Configuration section.",
        )

    def generate_upload_events():
        yield (
            "data: " + json.dumps({"type": "start", "total": len(html_files)}) + "\n\n"
        )

        success_count = 0
        for filepath in html_files:
            try:
                filename = os.path.basename(filepath)
                title = (
                    os.path.splitext(filename)[0]
                    .replace(file_group_identifier, "")
                    .replace("_", " ")
                    .title()
                    .strip()
                )

                with open(filepath, "r", encoding="utf-8") as f:
                    html_content = f.read()

                # Check if this is a homework file or weekly page
                if filename.startswith("homework_"):
                    # Handle homework assignment upload
                    hw_number = filename.split("_")[1]
                    title = f"Homework {hw_number}"

                    # Try to extract due date from HTML content if available
                    due_date = None
                    import re

                    due_match = re.search(r"(\d{1,2}/\d{1,2}/\d{4})", html_content)
                    if due_match:
                        due_date = due_match.group(1)

                    result = upload_homework_assignment(
                        title, html_content, course_id, access_token, due_date
                    )

                    if result.get("success"):
                        success_count += 1
                        yield (
                            "data: "
                            + json.dumps(
                                {
                                    "type": "success",
                                    "title": title,
                                    "assignment_id": result.get("assignment_id"),
                                    "url": result.get("url"),
                                    "current": success_count,
                                    "total": len(html_files),
                                    "item_type": "homework",
                                }
                            )
                            + "\n\n"
                        )
                    else:
                        yield (
                            "data: "
                            + json.dumps(
                                {
                                    "type": "error",
                                    "title": title,
                                    "error": result.get("error", "Unknown error"),
                                    "current": success_count,
                                    "total": len(html_files),
                                    "item_type": "homework",
                                }
                            )
                            + "\n\n"
                        )
                else:
                    # Handle weekly page upload
                    result = upload_page(title, html_content, course_id, access_token)
                    success_count += 1

                    yield (
                        "data: "
                        + json.dumps(
                            {
                                "type": "success",
                                "title": title,
                                "page_id": result.get("page_id"),
                                "url": result.get("url"),
                                "current": success_count,
                                "total": len(html_files),
                                "item_type": "page",
                            }
                        )
                        + "\n\n"
                    )

            except Exception as e:
                yield (
                    "data: "
                    + json.dumps(
                        {
                            "type": "error",
                            "title": title,
                            "error": str(e),
                            "current": success_count,
                            "total": len(html_files),
                            "item_type": "unknown",
                        }
                    )
                    + "\n\n"
                )

        yield (
            "data: "
            + json.dumps(
                {
                    "type": "complete",
                    "success_count": success_count,
                    "total": len(html_files),
                }
            )
            + "\n\n"
        )

    return StreamingResponse(
        generate_upload_events(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        },
    )


# returns a list of all of the generated files in the session based on the file_group_identifier
async def retrieve_generated_files(
    file_group_identifier: str = Cookie(None),
) -> List[str]:
    if not file_group_identifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file identifier found in cookies",
        )

    # look for generated HTML files in temp directory
    temp_dir = os.path.join("temp", file_group_identifier)
    print(file_group_identifier)
    if not os.path.exists(temp_dir):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Generated files not found"
        )

    # find all HTML files in the temp directory
    html_files = glob.glob(os.path.join(temp_dir, "*.html"))

    if not html_files:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No HTML files found to download",
        )

    return html_files
