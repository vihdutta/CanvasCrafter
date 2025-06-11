import os
import requests
import re


def upload_page(
    title: str, html_content: str, course_id: str = None, access_token: str = None
):
    if not course_id:
        raise ValueError(
            "Course ID is required. Please provide course_id parameter or set COURSE_ID environment variable."
        )

    if not access_token:
        raise ValueError(
            "Access Token is required. Please provide access_token parameter or set ACCESS_TOKEN environment variable."
        )

    headers = {"Authorization": f"Bearer {access_token}"}

    slug = re.sub(r"\W+", "_", title.lower()).strip("_")
    data = {
        "wiki_page[title]": title,
        "wiki_page[body]": html_content,
        "wiki_page[published]": True,
        "on_duplicate": "overwrite",
    }

    # try updating the page
    resp = requests.put(
        f"https://umich.instructure.com/api/v1/courses/{course_id}/pages/{slug}",
        headers=headers,
        data=data,
    )
    if resp.status_code == 404:
        # if page doesn't exist, then create the page
        data["wiki_page[page_url]"] = slug
        resp = requests.post(
            f"https://umich.instructure.com/api/v1/courses/{course_id}/pages",
            headers=headers,
            data=data,
        )

    resp.raise_for_status()
    return resp.json()


# upload all the files in the HTML_DIR to Canvas
if __name__ == "__main__":
    for filename in sorted(os.listdir("temp")):
        if not filename.lower().endswith(".html"):
            continue
        filepath = os.path.join("temp", filename)
        title = os.path.splitext(filename)[0].replace("_", " ").title()

        with open(filepath, "r", encoding="utf-8") as f:
            html_content = f.read()

        try:
            result = upload_page(title, html_content)
            print(
                f"Created page '{result['title']}' (ID: {result['page_id']}) at URL: {result['url']}"
            )
        except Exception as e:
            print(f"Failed to upload '{title}': {e}")
