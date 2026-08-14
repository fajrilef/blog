import json, sys
sys.path.insert(0, "/opt/data/web-blog-astro/scripts")
from sheet_helper import service

SID = "1JWgph214tsk9HFAeRyG5uhGicxU18RBGQ7O7nVN6CkY"
svc = service()
result = svc.spreadsheets().values().get(spreadsheetId=SID, range="Content Plan Living!A1:P60").execute()
rows = result.get("values", [])
for i, row in enumerate(rows):
    print(f"[{i}] " + "\t".join(row))
