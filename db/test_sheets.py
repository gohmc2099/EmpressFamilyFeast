"""Quick test to verify Google Sheets connection.

Run: python db/test_sheets.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

sheet_id = os.environ.get("GOOGLE_SHEET_ID", "")
creds_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "credentials.json")
creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON", "")

print(f"GOOGLE_SHEET_ID: {'SET (' + sheet_id[:20] + '...)' if sheet_id else 'NOT SET'}")
print(f"credentials.json: {'FOUND' if os.path.isfile(creds_file) else 'NOT FOUND at ' + creds_file}")
print(f"GOOGLE_CREDENTIALS_JSON env var: {'SET' if creds_json else 'NOT SET'}")
print()

if not sheet_id:
    print("ERROR: GOOGLE_SHEET_ID is not set in your .env file.")
    print("Add this line to your .env file:")
    print("  GOOGLE_SHEET_ID=your-spreadsheet-id-here")
    sys.exit(1)

if not os.path.isfile(creds_file) and not creds_json:
    print("ERROR: No credentials found.")
    print("Either place credentials.json in the project root,")
    print("or set GOOGLE_CREDENTIALS_JSON env var.")
    sys.exit(1)

print("Attempting to connect to Google Sheets...")
try:
    from db.google_sheets import get_sheets_db
    db = get_sheets_db(sheet_id)
    print("SUCCESS! Connected to Google Sheets.")
    print()
    worksheets = [ws.title for ws in db.spreadsheet.worksheets()]
    print(f"Tabs in your spreadsheet: {worksheets}")
    print()
    print("Google Sheets is working. Your dashboard will use it.")
except Exception as e:
    print(f"FAILED: {e}")
    print()
    print("Common fixes:")
    print("  1. Make sure you shared the Google Sheet with the service account email")
    print("  2. Check that the Sheet ID is correct")
    print("  3. Make sure Google Sheets API and Google Drive API are enabled")
