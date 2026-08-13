import json
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

TOKEN_PATH = "/opt/data/google_token.json"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
SID = "1JWgph214tsk9HFAeRyG5uhGicxU18RBGQ7O7nVN6CkY"

creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
    with open(TOKEN_PATH, "w") as f:
        f.write(creds.to_json())

svc = build("sheets", "v4", credentials=creds, cache_discovery=False)
result = svc.spreadsheets().values().get(spreadsheetId=SID, range="Content Plan Tech!A1:P80").execute()
rows = result.get("values", [])
for i, row in enumerate(rows):
    print(f"[{i}] " + "\t".join(row))
