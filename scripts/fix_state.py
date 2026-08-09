import json
from pathlib import Path

state_path = Path("/opt/data/web-blog-astro/.threads_comment_state.json")
state = json.loads(state_path.read_text()) if state_path.exists() else {}

# Hanya tips-keyboard-switch yang benar-benar sudah dipost ke Threads
state["posted_bank"] = ["tips-keyboard-switch"]
state_path.write_text(json.dumps(state, indent=2))

# Cek total bank & sisa
bank = json.loads(Path("/opt/data/web-blog-astro/scripts/threads_content_bank.json").read_text())
used = set(state["posted_bank"])
available = [i for i in bank if i["id"] not in used]
print(f"Bank total: {len(bank)} konten (20 original + 52 generate)")
print(f"Sudah dipost: {len(used)}")
print(f"Sisa tersedia: {len(available)}")
