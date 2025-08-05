import os
import re
import requests
import sys
from typing import List, Dict, Tuple
from dotenv import load_dotenv

load_dotenv()


class CanvasDeleter:
    def __init__(self, course_id: str, access_token: str):
        self.course_id = course_id
        self.access_token = access_token
        self.headers = {"Authorization": f"Bearer {access_token}"}
        self.base_url = "https://umich.instructure.com/api/v1"

    def get_all_pages(self) -> List[Dict]:
        pages = []
        url = f"{self.base_url}/courses/{self.course_id}/pages"

        while url:
            try:
                response = requests.get(url, headers=self.headers)
                response.raise_for_status()

                page_data = response.json()
                pages.extend(page_data)

                # Check for pagination
                links = response.headers.get("Link", "")
                url = None
                for link in links.split(","):
                    if 'rel="next"' in link:
                        url = link.split(";")[0].strip("<>")
                        break

            except requests.exceptions.RequestException as e:
                print(f"Error fetching pages: {e}")
                break

        return pages

    def get_all_assignments(self) -> List[Dict]:
        """
        Retrieve all assignments from the Canvas course.

        Returns:
            List of assignment dictionaries from Canvas API
        """
        assignments = []
        url = f"{self.base_url}/courses/{self.course_id}/assignments"

        while url:
            try:
                response = requests.get(url, headers=self.headers)
                response.raise_for_status()

                assignment_data = response.json()
                assignments.extend(assignment_data)

                # Check for pagination
                links = response.headers.get("Link", "")
                url = None
                for link in links.split(","):
                    if 'rel="next"' in link:
                        url = link.split(";")[0].strip("<>")
                        break

            except requests.exceptions.RequestException as e:
                print(f"Error fetching assignments: {e}")
                break

        return assignments

    def filter_pages_to_delete(self, pages: List[Dict]) -> List[Dict]:
        pages_to_delete = []

        # Patterns to match: "Week #" (simple format), "Week #: Topic (Date)" (detailed format), and "HW##"
        week_pattern = re.compile(r"^Week\s+\d+.*$", re.IGNORECASE)
        homework_pattern = re.compile(r"^HW\d{2}$", re.IGNORECASE)

        for page in pages:
            title = page.get("title", "")
            if week_pattern.match(title) or homework_pattern.match(title):
                pages_to_delete.append(page)

        return pages_to_delete

    def filter_assignments_to_delete(self, assignments: List[Dict]) -> List[Dict]:
        """
        Filter assignments that match the deletion criteria: "Checkout#", "Quiz #", and "HW##"

        Args:
            assignments: List of all assignments from Canvas

        Returns:
            List of assignments that should be deleted
        """
        assignments_to_delete = []

        # Patterns to match: "Checkout#", "Quiz #", and "HW##"
        checkout_pattern = re.compile(r"^Checkout\d+$", re.IGNORECASE)
        quiz_pattern = re.compile(r"^Quiz\s+\d+$", re.IGNORECASE)
        homework_pattern = re.compile(r"^HW\d{2}$", re.IGNORECASE)

        for assignment in assignments:
            name = assignment.get("name", "")
            if (checkout_pattern.match(name) or 
                quiz_pattern.match(name) or 
                homework_pattern.match(name)):
                assignments_to_delete.append(assignment)

        return assignments_to_delete

    def delete_page(self, page: Dict) -> bool:
        """
        Delete a single Canvas page.

        Args:
            page: Page dictionary from Canvas API

        Returns:
            True if deletion was successful, False otherwise
        """
        page_url = page.get("url")
        title = page.get("title")

        try:
            url = f"{self.base_url}/courses/{self.course_id}/pages/{page_url}"
            response = requests.delete(url, headers=self.headers)
            response.raise_for_status()

            print(f"✓ Deleted page: '{title}'")
            return True

        except requests.exceptions.RequestException as e:
            print(f"✗ Failed to delete page '{title}': {e}")
            return False

    def delete_assignment(self, assignment: Dict) -> bool:
        """
        Delete a single Canvas assignment.

        Args:
            assignment: Assignment dictionary from Canvas API

        Returns:
            True if deletion was successful, False otherwise
        """
        assignment_id = assignment.get("id")
        name = assignment.get("name")

        try:
            url = (
                f"{self.base_url}/courses/{self.course_id}/assignments/{assignment_id}"
            )
            response = requests.delete(url, headers=self.headers)
            response.raise_for_status()

            print(f"✓ Deleted assignment: '{name}'")
            return True

        except requests.exceptions.RequestException as e:
            print(f"✗ Failed to delete assignment '{name}': {e}")
            return False

    def delete_all_matching_items(self) -> Tuple[int, int]:
        print("🔍 Fetching Canvas items...")

        all_pages = self.get_all_pages()
        all_assignments = self.get_all_assignments()

        print(
            f"Found {len(all_pages)} total pages and {len(all_assignments)} total assignments"
        )

        pages_to_delete = self.filter_pages_to_delete(all_pages)
        assignments_to_delete = self.filter_assignments_to_delete(all_assignments)

        print(f"\n📋 Items matching deletion criteria:")
        print(f"  - Pages to delete: {len(pages_to_delete)}")
        print(f"  - Assignments to delete: {len(assignments_to_delete)}")

        if not pages_to_delete and not assignments_to_delete:
            print("\n✅ No items found matching the deletion criteria.")
            return 0, 0

        print("\n📝 Items that will be deleted:")
        print("Pages:")
        for page in pages_to_delete:
            print(f"  - {page.get('title')}")

        print("Assignments:")
        for assignment in assignments_to_delete:
            print(f"  - {assignment.get('name')}")

        total_items = len(pages_to_delete) + len(assignments_to_delete)
        confirm = input(
            f"\n⚠️  Are you sure you want to delete {total_items} items? (yes/no): "
        )

        if confirm.lower() != "yes":
            print("❌ Deletion cancelled.")
            return 0, 0

        print(f"\n🗑️  Deleting items...")

        pages_deleted = 0
        for page in pages_to_delete:
            if self.delete_page(page):
                pages_deleted += 1

        assignments_deleted = 0
        for assignment in assignments_to_delete:
            if self.delete_assignment(assignment):
                assignments_deleted += 1

        print(f"\n✅ Deletion complete!")
        print(f"  - Pages deleted: {pages_deleted}/{len(pages_to_delete)}")
        print(
            f"  - Assignments deleted: {assignments_deleted}/{len(assignments_to_delete)}"
        )

        return pages_deleted, assignments_deleted


def get_credentials() -> Tuple[str, str]:
    course_id = os.getenv("COURSE_ID")
    access_token = os.getenv("ACCESS_TOKEN")

    if not course_id or not access_token:
        raise Exception(
            "COURSE_ID and ACCESS_TOKEN must be set as environment variables"
        )

    return course_id, access_token


def main():
    """Main function to run the deletion script."""
    print("🧹 Canvas Item Deletion Script")
    print("=" * 50)
    print("This script will delete Canvas items with these formats:")
    print("  - Pages: 'Week #' (and variations like 'Week #: Topic (Date)') and 'HW##'")
    print("  - Assignments: 'Checkout#', 'Quiz #', and 'HW##'")
    print()

    course_id, access_token = get_credentials()
    deleter = CanvasDeleter(course_id, access_token)
    pages_deleted, assignments_deleted = deleter.delete_all_matching_items()

    print(
        f"\n📊 Summary: Deleted {pages_deleted} pages and {assignments_deleted} assignments"
    )


if __name__ == "__main__":
    main()
