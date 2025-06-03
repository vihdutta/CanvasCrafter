import os
import requests
import re
from dotenv import load_dotenv

load_dotenv()

# config
API_BASE_URL = os.getenv("API_BASE_URL")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
COURSE_ID = os.getenv("COURSE_ID")
HTML_DIR = os.getenv("HTML_DIR", "temp")

headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

def upload_page(title: str, html_content: str):
    slug = re.sub(r'\W+', '_', title.lower()).strip('_')
    data = {
        "wiki_page[title]": title,
        "wiki_page[body]": html_content,
        "wiki_page[published]": True,
        "on_duplicate": "overwrite"
    }

    # try updating the page
    resp = requests.put(
        f"{API_BASE_URL}/courses/{COURSE_ID}/pages/{slug}",
        headers=headers, data=data
    )
    if resp.status_code == 404:
        # if page doesn't exist, then create the page
        data["wiki_page[page_url]"] = slug
        resp = requests.post(
            f"{API_BASE_URL}/courses/{COURSE_ID}/pages",
            headers=headers, data=data
        )

    resp.raise_for_status()
    return resp.json()

# upload all the files in the HTML_DIR to Canvas
if __name__ == "__main__":
    for filename in sorted(os.listdir(HTML_DIR)):
        if not filename.lower().endswith(".html"):
            continue
        filepath = os.path.join(HTML_DIR, filename)
        title = os.path.splitext(filename)[0].replace("_", " ").title()

        with open(filepath, "r", encoding="utf-8") as f:
            html_content = f.read()

        try:
            result = upload_page(title, html_content)
            print(f"Created page '{result['title']}' (ID: {result['page_id']}) at URL: {result['url']}")
        except Exception as e:
            print(f"Failed to upload '{title}': {e}")