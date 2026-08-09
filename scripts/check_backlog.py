import json, re
from pathlib import Path

state_file = Path("/opt/data/web-blog-astro/.threads_comment_state.json")
state = json.loads(state_file.read_text()) if state_file.exists() else {}
posted = set(state.get("posted_articles", []))

content_dir = Path("/opt/data/web-blog-astro/src/content/blog")
total = 0
unposted = []
for cat in ["tech", "living"]:
    for md in (content_dir / cat).glob("*.mdx"):
        content = md.read_text()
        fm = re.match(r"---\n(.*?)\n---", content, re.DOTALL)
        if not fm:
            continue
        fm_text = {}
        for line in fm.group(1).split("\n"):
            if ":" in line:
                k, v = line.split(":", 1)
                fm_text[k.strip()] = v.strip().strip('"')
        if fm_text.get("draft", "").lower() == "true":
            continue
        total += 1
        if md.stem not in posted:
            unposted.append((cat, md.stem, fm_text.get("pubDate", "")))

print(f"Total artikel live: {total}")
print(f"Sudah dipost Threads: {len(posted)}")
print(f"Backlog (belum dipost): {len(unposted)}")
print("\nBacklog list:")
for cat, slug, pub in sorted(unposted, key=lambda x: x[2], reverse=True):
    print(f"  [{cat}] {slug} ({pub})")
