#!/usr/bin/env python3
"""Read Content Plan Living sheet."""
import json, subprocess, sys

GOOGLE_API = "/opt/data/skills/productivity/google-workspace/scripts/google_api.py"
SID = "1JWgph214tsk9HFAeRyG5uhGicxU18RBGQ7O7nVN6CkY"
PY = "/opt/data/gws-venv/bin/python"

out = subprocess.run(
    [PY, GOOGLE_API, "sheets", "get", SID, sys.argv[1]],
    capture_output=True, text=True, timeout=120,
)
if out.returncode != 0:
    print("ERROR:", out.stderr)
    sys.exit(1)
data = json.loads(out.stdout)
for row in data:
    print("\t".join(str(c) for c in row))