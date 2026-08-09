#!/usr/bin/env python3
"""Helper tipis untuk baca/tulis Google Sheets (Content Plan Lofa).
Pakai token yang sudah ada: /opt/data/google_token.json
Usage:
  sheet_helper.py get SID RANGE
  sheet_helper.py update SID RANGE '[[...]]'
  sheet_helper.py append SID RANGE '[[...]]'
"""
import json
import sys
from datetime import datetime, timedelta, timezone

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

TOKEN_PATH = "/opt/data/google_token.json"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def get_creds():
    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
    return creds


def service():
    return build("sheets", "v4", credentials=get_creds(), cache_discovery=False)


def main():
    cmd = sys.argv[1]
    sid = sys.argv[2]
    rng = sys.argv[3]
    svc = service()
    if cmd == "get":
        result = (
            svc.spreadsheets()
            .values()
            .get(spreadsheetId=sid, range=rng)
            .execute()
        )
        print(json.dumps(result.get("values", []), ensure_ascii=False))
    elif cmd == "update":
        values = json.loads(sys.argv[4])
        result = (
            svc.spreadsheets()
            .values()
            .update(
                spreadsheetId=sid,
                range=rng,
                valueInputOption="RAW",
                body={"values": values},
            )
            .execute()
        )
        print(json.dumps({"updated": result.get("updatedCells", 0)}))
    elif cmd == "append":
        values = json.loads(sys.argv[4])
        result = (
            svc.spreadsheets()
            .values()
            .append(
                spreadsheetId=sid,
                range=rng,
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={"values": values},
            )
            .execute()
        )
        print(json.dumps({"updated": result.get("updates", {}).get("updatedRows", 0)}))


if __name__ == "__main__":
    main()
