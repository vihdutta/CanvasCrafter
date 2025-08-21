from typing import List
import uuid
import os
import glob
import json
import pickle
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
from files.backend.build_htmls.build_quiz import upload_quiz_assignment
from files.backend.build_htmls.build_checkout import upload_checkout_assignment
from files.backend.populate_weeks_utils import get_week_title_with_topic_and_date

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
        course_id=None,  # Canvas credentials not available in this endpoint
        access_token=None,
        lecture_info_path="files/yaml/lecture_info.yaml"
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

        # Load weeks_data for proper title generation
        weeks_data_file = os.path.join(temp_dir, "weeks_data.pkl")
        weeks_data = None
        if os.path.exists(weeks_data_file):
            try:
                with open(weeks_data_file, "rb") as f:
                    weeks_data = pickle.load(f)
            except Exception as e:
                print(f"Warning: Could not load weeks_data.pkl: {e}")

        # Separate weekly pages from homework files
        weekly_files = []
        homework_files = []
        quiz_files = []
        checkout_files = []

        for html_file in html_files:
            filename = os.path.basename(html_file)
            if filename.startswith("homework_"):
                # homework file
                hw_number = filename.split("_")[1]
                with open(html_file, "r", encoding="utf-8") as f:
                    html_content = f.read()

                homework_files.append(
                    {
                        "name": f"HW{int(hw_number):02d}",
                        "html": html_content,
                        "type": "homework",
                        "hw_number": hw_number,
                    }
                )
            elif filename.startswith("quiz_"):
                # quiz file
                quiz_number = filename.split("_")[1]
                with open(html_file, "r", encoding="utf-8") as f:
                    html_content = f.read()

                quiz_files.append(
                    {
                        "name": f"Quiz{quiz_number}",
                        "html": html_content,
                        "type": "quiz",
                        "quiz_number": quiz_number,
                    }
                )
            elif filename.startswith("checkout_"):
                # checkout file
                checkout_number = filename.split("_")[1]
                with open(html_file, "r", encoding="utf-8") as f:
                    html_content = f.read()

                checkout_files.append(
                    {
                        "name": f"Checkout{checkout_number}",
                        "html": html_content,
                        "type": "checkout",
                        "checkout_number": checkout_number,
                    }
                )
            elif filename.startswith("week_"):
                # weekly page file - extract week number and generate proper title
                week_number_str = filename.replace(f"_{unique_identifier}.html", "").replace("week_", "")
                try:
                    display_week_num = int(week_number_str)
                    if weeks_data:
                        week_name = get_week_title_with_topic_and_date(weeks_data, display_week_num)
                    else:
                        # Fallback to old format if weeks_data not available
                        week_name = f"Week {display_week_num}"
                except ValueError:
                    # Fallback to old format if parsing fails
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

        # Sort quiz files numerically by quiz number
        def get_quiz_number(item):
            try:
                return int(item.get("quiz_number", "0"))
            except (ValueError, AttributeError):
                return float("inf")

        quiz_files = sorted(quiz_files, key=get_quiz_number)

        # Sort checkout files numerically by checkout number
        def get_checkout_number(item):
            try:
                return int(item.get("checkout_number", "0"))
            except (ValueError, AttributeError):
                return float("inf")

        checkout_files = sorted(checkout_files, key=get_checkout_number)

        # Combine weekly, homework, quiz, and checkout files
        all_files = weekly_files + homework_files + quiz_files + checkout_files

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
        homework_urls = {}  # Dictionary to store homework assignment URLs
        quiz_urls = {}  # Dictionary to store quiz assignment URLs
        checkout_urls = {}  # Dictionary to store checkout assignment URLs
        
        # Separate homework, quiz, checkout, and weekly files
        homework_files = [f for f in html_files if os.path.basename(f).startswith("homework_")]
        quiz_files = [f for f in html_files if os.path.basename(f).startswith("quiz_")]
        checkout_files = [f for f in html_files if os.path.basename(f).startswith("checkout_")]
        weekly_files = [f for f in html_files if not os.path.basename(f).startswith("homework_") and not os.path.basename(f).startswith("quiz_") and not os.path.basename(f).startswith("checkout_")]
        
        # Load weeks_data for proper title generation
        temp_dir = os.path.join("temp", file_group_identifier)
        weeks_data_file = os.path.join(temp_dir, "weeks_data.pkl")
        weeks_data = None
        if os.path.exists(weeks_data_file):
            try:
                with open(weeks_data_file, "rb") as f:
                    weeks_data = pickle.load(f)
            except Exception as e:
                print(f"Warning: Could not load weeks_data.pkl: {e}")
        
        # STEP 1: Upload homework assignments FIRST
        for filepath in homework_files:
            try:
                filename = os.path.basename(filepath)
                hw_number = filename.split("_")[1]
                title = f"HW{int(hw_number):02d}"

                with open(filepath, "r", encoding="utf-8") as f:
                    html_content = f.read()

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
                    assignment_id = result.get("assignment_id")
                    # Store the homework URL for linking in weekly pages
                    homework_urls[title] = f"https://umich.instructure.com/courses/{course_id}/assignments/{assignment_id}"
                    
                    yield (
                        "data: "
                        + json.dumps(
                            {
                                "type": "success",
                                "title": title,
                                "assignment_id": assignment_id,
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
                            "item_type": "homework",
                        }
                    )
                    + "\n\n"
                )
        
        # STEP 2: Upload quiz assignments SECOND
        for filepath in quiz_files:
            try:
                filename = os.path.basename(filepath)
                quiz_number = filename.split("_")[1]
                title = f"Quiz{quiz_number}"

                with open(filepath, "r", encoding="utf-8") as f:
                    html_content = f.read()

                # Get the proper quiz date from weeks_data instead of parsing HTML
                quiz_date = None
                if weeks_data:
                    from files.backend.populate_weeks_utils import collect_quiz_dates
                    all_quizzes = collect_quiz_dates(weeks_data)
                    # Find the quiz with matching quiz_number
                    for quiz in all_quizzes:
                        if str(quiz["quiz_number"]) == quiz_number:
                            quiz_date = quiz["date"]
                            break
                
                # Fallback: try to extract quiz date from HTML content if not found in weeks_data
                if not quiz_date:
                    import re
                    date_match = re.search(r"(\d{1,2}/\d{1,2}/\d{4})", html_content)
                    if date_match:
                        quiz_date = date_match.group(1)

                result = upload_quiz_assignment(
                    title, html_content, course_id, access_token, quiz_date
                )

                if result.get("success"):
                    success_count += 1
                    assignment_id = result.get("assignment_id")
                    # Store the quiz URL for linking in weekly pages
                    quiz_urls[title] = f"https://umich.instructure.com/courses/{course_id}/assignments/{assignment_id}"
                    
                    yield (
                        "data: "
                        + json.dumps(
                            {
                                "type": "success",
                                "title": title,
                                "assignment_id": assignment_id,
                                "url": result.get("url"),
                                "current": success_count,
                                "total": len(html_files),
                                "item_type": "quiz",
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
                                "item_type": "quiz",
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
                            "item_type": "quiz",
                        }
                    )
                    + "\n\n"
                )
        
        # STEP 3: Upload checkout assignments THIRD (after homework and quiz, since they reference homework)
        # First, regenerate checkout HTML with homework URLs for proper linking
        if weeks_data and homework_urls:
            try:
                from files.backend.build_htmls.build_checkout import build_checkout_html
                updated_checkout_files = build_checkout_html(weeks_data, file_group_identifier, course_id, homework_urls)
                # Update the checkout_files list to use the regenerated files
                checkout_files = updated_checkout_files
            except Exception as e:
                print(f"Warning: Could not regenerate checkout files with homework URLs: {e}")
        
        for filepath in checkout_files:
            try:
                filename = os.path.basename(filepath)
                checkout_number = filename.split("_")[1]
                title = f"Checkout{checkout_number}"

                with open(filepath, "r", encoding="utf-8") as f:
                    html_content = f.read()

                # Try to extract due date from HTML content if available
                due_date = None
                import re
                due_match = re.search(r"(\d{1,2}/\d{1,2}/\d{4})", html_content)
                if due_match:
                    due_date = due_match.group(1)

                result = upload_checkout_assignment(
                    title, html_content, course_id, access_token, due_date
                )

                if result.get("success"):
                    success_count += 1
                    assignment_id = result.get("assignment_id")
                    # Store the checkout URL for linking in weekly pages if needed
                    checkout_urls[title] = f"https://umich.instructure.com/courses/{course_id}/assignments/{assignment_id}"
                    
                    yield (
                        "data: "
                        + json.dumps(
                            {
                                "type": "success",
                                "title": title,
                                "assignment_id": assignment_id,
                                "url": result.get("url"),
                                "current": success_count,
                                "total": len(html_files),
                                "item_type": "checkout",
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
                                "item_type": "checkout",
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
                            "item_type": "checkout",
                        }
                    )
                    + "\n\n"
                )
        
        # STEP 4: Regenerate weekly pages with homework URLs, quiz URLs, and checkout URLs and upload them
        try:
            # Get the original weeks data to regenerate pages with homework and quiz links
            temp_dir = os.path.join("temp", file_group_identifier)
            
            # We need to reconstruct the weeks data from the generated files
            # For now, we'll regenerate the weekly pages with the homework URLs and quiz URLs
            from files.backend.build_htmls.build_weekly_page import regenerate_weekly_pages_with_homework_urls
            
            updated_weekly_files = regenerate_weekly_pages_with_homework_urls(
                temp_dir, homework_urls, course_id, quiz_urls, checkout_urls, access_token
            )
            
        except Exception as e:
            # If regeneration fails, proceed with original weekly files
            print(f"Warning: Could not regenerate weekly pages with homework and quiz URLs: {e}")
            updated_weekly_files = weekly_files
        
        # STEP 5: Upload the weekly pages
        for filepath in updated_weekly_files:
            try:
                filename = os.path.basename(filepath)
                
                # Extract week number and generate proper title
                base_filename = os.path.splitext(filename)[0].replace(file_group_identifier, "").strip()
                if base_filename.startswith("week_"):
                    week_number_str = base_filename.replace("week_", "").replace("_", "")
                    try:
                        display_week_num = int(week_number_str)
                        if weeks_data:
                            title = get_week_title_with_topic_and_date(weeks_data, display_week_num)
                        else:
                            # Fallback to old format if weeks_data not available
                            title = f"Week {display_week_num}"
                    except ValueError:
                        # Fallback to old format if parsing fails
                        title = base_filename.replace("_", " ").title()
                else:
                    # Fallback to old format for non-weekly files
                    title = base_filename.replace("_", " ").title()

                with open(filepath, "r", encoding="utf-8") as f:
                    html_content = f.read()

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
                            "item_type": "page",
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
