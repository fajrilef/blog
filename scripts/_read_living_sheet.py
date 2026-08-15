#!/usr/bin/env python3
import json, subprocess, sys
GOOGLE_API = "/opt/data/skills/productivity/google-workspace/scripts/google_api.py"
SID = "1JWgph214tsk9HFAeRyG5uhGicxU18RBGQ7O7nVN6CkY"
PY = "/opt/data/gws-venv/bin/python"
rng = sys.argv[1] if len(sys.argv) > 1 else "Content Plan Living!A1:P80"
out = subprocess.run([PY, GOOGLE_API, "sheets", "get", SID, rng], capture_output=True, text=True, timeout=120)
if out.returncode != 0:
    print("ERROR:", out.stderr)
    sys.exit(1)
data = json.loads(out.stdout)
for i, row in enumerate(data):
    print(f"[{i}] " + "\t".join(str(c) for c in row))
