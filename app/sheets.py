"""
sheets.py — Google Sheets Integration
======================================
Appends one row per student to a tracking spreadsheet.
Columns: Timestamp | Student Name | Course Level | Instrument | Month | Feedback Summary | Action Point 1 | Action Point 2 | Action Point 3 | Page URL

Note: Called with try/except in main.py — a Sheets failure will NOT crash the pipeline.
"""

import os
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

SHEET_ID   = os.getenv("GOOGLE_SHEET_ID")
SHEET_NAME = "Feedback Log"   # must match your tab name exactly


def _get_sheets_service():
    creds = Credentials.from_service_account_file(
        os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "service_account.json"),
        scopes=SCOPES,
    )
    return build("sheets", "v4", credentials=creds)


def append_to_sheet(student_data: dict, doc_url: str = "") -> None:
    """Append one row of student data to the tracking sheet."""
    service = _get_sheets_service()

    action_points = list(student_data.get("action_points", []))
    # Pad to exactly 3 slots
    while len(action_points) < 3:
        action_points.append("")

    row = [
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        student_data.get("student_name", ""),
        student_data.get("course_level", ""),
        student_data.get("instrument", ""),
        student_data.get("month", ""),
        student_data.get("feedback_summary", ""),
        action_points[0],
        action_points[1],
        action_points[2],
        doc_url,
    ]

    service.spreadsheets().values().append(
        spreadsheetId=SHEET_ID,
        range=f"{SHEET_NAME}!A:J",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": [row]},
    ).execute()
    print(f"✅ Sheet row appended for: {student_data.get('student_name')}")


def ensure_sheet_headers() -> None:
    """
    Call once to ensure the sheet has proper column headers.
    Safe to call repeatedly — only writes if row 1 is empty.
    """
    service = _get_sheets_service()

    result = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID,
        range=f"{SHEET_NAME}!A1:J1",
    ).execute()

    if not result.get("values"):
        headers = [[
            "Timestamp", "Student Name", "Course Level", "Instrument",
            "Month", "Feedback Summary",
            "Action Point 1", "Action Point 2", "Action Point 3",
            "Page URL",
        ]]
        service.spreadsheets().values().update(
            spreadsheetId=SHEET_ID,
            range=f"{SHEET_NAME}!A1:J1",
            valueInputOption="RAW",
            body={"values": headers},
        ).execute()
        print("✅ Sheet headers created.")