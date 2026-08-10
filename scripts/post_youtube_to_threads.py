#!/usr/bin/env python3
"""
Auto-post video YouTube terbaru dari channel Lofa Shorts ke Threads.
Deteksi via RSS feed publik (gratis, tanpa API key).

Alur:
1. Baca RSS feed channel → ambil video terbaru (by published date)
2. Cek state: video sudah pernah dipost?
3. Belum → post ke Threads (judul + link) + komen affiliate (jeda 1-5 menit)
4. Tandai video sudah dipost

Cron: tiap 30 menit (script ini exit cepat kalau tidak ada video baru).
"""

import os
import sys
import re
import json
import time
import random
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime

# Load .env
def load_env():
    env_path = Path("/opt/data/.env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key] = val

load_env()

CHANNEL_ID = "UCi7CO-AEgwHUVn70jEzZRaQ"
RSS_URL = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"
STATE_FILE = Path("/opt/data/web-blog-astro/.threads_youtube_state.json")

THREADS_ACCESS_TOKEN = os.getenv("THREADS_ACCESS_TOKEN")
THREADS_USER_ID = os.getenv("THREADS_USER_ID")
THREADS_API_BASE = "https://graph.threads.net/v1.0"


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def get_latest_video() -> dict | None:
    """Ambil video terbaru dari RSS feed channel."""
    req = urllib.request.Request(RSS_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        xml_data = r.read().decode("utf-8")
    
    ns = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
    root = ET.fromstring(xml_data)
    
    videos = []
    for entry in root.findall("atom:entry", ns):
        video_id_el = entry.find("yt:videoId", ns)
        title_el = entry.find("atom:title", ns)
        published_el = entry.find("atom:published", ns)
        author_el = entry.find("atom:author/atom:name", ns)
        if video_id_el is None or title_el is None or published_el is None:
            continue
        videos.append({
            "id": video_id_el.text,
            "title": title_el.text or "",
            "published": published_el.text or "",
            "author": author_el.text if author_el is not None else "",
            "url": f"https://youtu.be/{video_id_el.text}",
        })
    
    # Sort by published desc
    videos.sort(key=lambda v: v["published"], reverse=True)
    return videos[0] if videos else None


def api_call(method: str, path: str, data: dict | None = None) -> dict:
    url = f"{THREADS_API_BASE}{path}"
    if method == "GET":
        url += "?" + urllib.parse.urlencode(data or {})
        req = urllib.request.Request(url, method="GET")
    else:
        encoded = urllib.parse.urlencode(data or {}).encode("utf-8")
        req = urllib.request.Request(url, data=encoded, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"error": e.read().decode("utf-8"), "status": e.code}


def post_to_threads(text: str) -> dict:
    """Post ke Threads (text-only, tanpa preview card)."""
    if not THREADS_ACCESS_TOKEN or not THREADS_USER_ID:
        return {"success": False, "error": "Missing THREADS_ACCESS_TOKEN/USER_ID"}
    
    create_data = {
        "access_token": THREADS_ACCESS_TOKEN,
        "media_type": "TEXT",
        "text": text,
    }
    resp = api_call("POST", f"/{THREADS_USER_ID}/threads", create_data)
    if "error" in resp:
        return {"success": False, "error": f"Create failed: {resp['error']}"}
    creation_id = resp.get("id")
    if not creation_id:
        return {"success": False, "error": f"No creation_id: {resp}"}
    
    time.sleep(5)
    
    publish_data = {"access_token": THREADS_ACCESS_TOKEN, "creation_id": creation_id}
    for attempt in range(1, 4):
        resp = api_call("POST", f"/{THREADS_USER_ID}/threads_publish", publish_data)
        if "error" not in resp:
            return {"success": True, "post_id": resp.get("id")}
        err = str(resp.get("error", ""))[:80]
        print(f"   ⏳ Publish attempt {attempt} gagal ({err}...), retry...")
        time.sleep(8 * attempt)
    return {"success": False, "error": f"Publish failed: {resp}"}


def post_comment(post_id: str, text: str) -> dict:
    """Komen di post (dengan retry)."""
    create_data = {
        "access_token": THREADS_ACCESS_TOKEN,
        "media_type": "TEXT",
        "text": text,
        "reply_to_id": post_id,
    }
    resp = api_call("POST", f"/{THREADS_USER_ID}/threads", create_data)
    if "error" in resp:
        return {"success": False, "error": f"Create reply failed: {resp['error']}"}
    creation_id = resp.get("id")
    if not creation_id:
        return {"success": False, "error": f"No creation_id: {resp}"}
    
    time.sleep(5)
    publish_data = {"access_token": THREADS_ACCESS_TOKEN, "creation_id": creation_id}
    for attempt in range(1, 4):
        resp = api_call("POST", f"/{THREADS_USER_ID}/threads_publish", publish_data)
        if "error" not in resp:
            return {"success": True, "comment_id": resp.get("id")}
        err = str(resp.get("error", ""))[:80]
        print(f"   ⏳ Publish attempt {attempt} gagal ({err}...), retry...")
        time.sleep(8 * attempt)
    return {"success": False, "error": f"Publish failed: {resp}"}


def get_affiliate_products() -> list:
    """Ambil produk affiliate dari products.ts."""
    products_path = Path("/opt/data/web-blog-astro/src/lib/products.ts")
    if not products_path.exists():
        return []
    content = products_path.read_text(encoding="utf-8")
    products = []
    blocks = re.findall(r"'([^']+)': \{\n(.*?)\n  \},", content, re.DOTALL)
    for pid, body in blocks:
        name = re.search(r"name: '([^']+)'", body)
        url = re.search(r"affiliateUrl: '([^']+)'", body)
        if name and url:
            products.append({"id": pid, "name": name.group(1), "url": url.group(1)})
    return products


def build_comment_text(product: dict) -> str:
    """Teks komen affiliate natural & singkat."""
    name = product["name"]
    url = product["url"]
    # Singkatkan nama produk
    short = name.strip()
    lower = short.lower()
    patterns = [
        (r"mechanical keyboard.*", "keyboard mechanical"),
        (r"keyboard.*gaming.*", "keyboard gaming"),
        (r"ram laptop", "RAM laptop"),
        (r"kain lap microfiber.*", "kain lap microfiber"),
        (r"kotak penyimpanan.*", "kotak penyimpanan"),
        (r"plastik (zip.?lock|klip).*", "plastik ziplock"),
        (r"food box.*|wadah makanan.*", "wadah makanan kedap udara"),
        (r"storage box.*", "storage box"),
    ]
    for pattern, s in patterns:
        if re.search(pattern, lower):
            short = s
            break
    else:
        words = short.split()
        if len(words) > 5:
            short = " ".join(words[:4]).rstrip(",").lower()
        else:
            short = short.lower()
    
    texts = [
        f"Btw, buat yang lagi nyari {short}, aku nemu yang bagus dan harganya oke. Cek: {url}",
        f"Btw soal ini, kalau butuh {short} yang worth it, aku rekomen yang ini: {url}",
        f"Ngomong-ngomong, buat yang cari {short}, ini yang aku pakai dan oke banget: {url}",
    ]
    return texts[0]


def main():
    dry_run = "--dry-run" in sys.argv
    
    if not THREADS_ACCESS_TOKEN or not THREADS_USER_ID:
        print("❌ THREADS_ACCESS_TOKEN / THREADS_USER_ID belum di-set di .env")
        sys.exit(1)
    
    # 1) Ambil video terbaru
    video = get_latest_video()
    if not video:
        print("❌ Gagal ambil RSS feed YouTube")
        sys.exit(1)
    
    print(f"📺 Video terbaru: {video['title'][:60]}...")
    print(f"   Link: {video['url']}")
    
    # 2) Cek sudah dipost?
    state = load_state()
    posted = set(state.get("posted_videos", []))
    if video["id"] in posted:
        print("ℹ️ Video sudah pernah dipost ke Threads. Tidak ada video baru.")
        return
    
    # 3) Post ke Threads
    post_text = f"Baru nih di channel! 🎬\n\n{video['title']}\n\n👇 Tonton videonya di sini:\n{video['url']}"
    print("\n--- POST PREVIEW ---")
    print(post_text)
    print("---\n")
    
    if dry_run:
        print("(dry-run, tidak posting)")
        return
    
    result = post_to_threads(post_text)
    if not result["success"]:
        print(f"❌ Post gagal: {result['error']}")
        sys.exit(1)
    post_id = result["post_id"]
    print(f"✅ Posted! Post ID: {post_id}")
    
    # Tandai sudah dipost
    posted.add(video["id"])
    state["posted_videos"] = sorted(posted)
    save_state(state)
    
    # 4) Jeda 1-5 menit, lalu komen affiliate
    delay = random.randint(60, 300)
    print(f"⏳ Jeda {delay} detik (1-5 menit) sebelum komen affiliate...")
    time.sleep(delay)
    
    products = get_affiliate_products()
    candidates = [p for p in products if p.get("url")]
    if candidates:
        product = random.choice(candidates)
        comment_text = build_comment_text(product)
        print(f"💬 Komen affiliate: {comment_text[:60]}...")
        r = post_comment(post_id, comment_text)
        if r.get("success"):
            print(f"✅ Komen affiliate OK: {r['comment_id']}")
        else:
            print(f"⚠️ Komen affiliate gagal: {r.get('error', r)}")
    
    print(f"\n✅ Selesai! Post: https://www.threads.net/@lofaonline/post/{post_id}")


if __name__ == "__main__":
    main()
