#!/usr/bin/env python3
"""
Auto-post blog articles to Threads (Threads API resmi)
Usage: python3 post_to_threads.py [--article-slug SLUG] [--category tech|living] [--dry-run] [--text "Teks custom"]
"""

import os
import sys
import json
import re
import argparse
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from datetime import datetime

# Load .env manually
def load_env():
    env_path = Path("/opt/data/.env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key] = val

load_env()

THREADS_API_BASE = "https://graph.threads.net/v1.0"

# Config dari .env
THREADS_ACCESS_TOKEN = os.getenv("THREADS_ACCESS_TOKEN")
THREADS_USER_ID = os.getenv("THREADS_USER_ID")
BLOG_BASE_URL = "https://lofa.web.id"


def get_latest_article(category: str | None = None, skip_posted: bool = True) -> dict | None:
    """Get the latest published article from the blog content.
    
    skip_posted=True: skip artikel yang sudah pernah dipost ke Threads
    (tracking di STATE_FILE → posted_articles).
    """
    content_dir = Path("/opt/data/web-blog-astro/src/content/blog")
    
    # Slug yang sudah dipost ke Threads
    posted = set(load_state().get("posted_articles", []))
    
    articles = []
    for cat in ["tech", "living"]:
        if category and cat != category:
            continue
        cat_path = content_dir / cat
        if not cat_path.exists():
            continue
        for md_file in cat_path.glob("*.mdx"):
            content = md_file.read_text(encoding="utf-8")
            fm_match = re.match(r"---\n(.*?)\n---", content, re.DOTALL)
            if fm_match:
                fm_text = fm_match.group(1)
                fm = {}
                for line in fm_text.split("\n"):
                    if ":" in line:
                        key, val = line.split(":", 1)
                        fm[key.strip()] = val.strip().strip('"')
                
                # Skip drafts
                if fm.get("draft", "").lower() == "true":
                    continue
                
                slug = md_file.stem
                if skip_posted and slug in posted:
                    continue
                
                articles.append({
                    "slug": slug,
                    "category": cat,
                    "title": fm.get("title", ""),
                    "description": fm.get("description", ""),
                    "pubDate": fm.get("pubDate", ""),
                    "tags": fm.get("tags", ""),
                    "cover": fm.get("cover", ""),
                })
    
    if not articles:
        return None
    
    # Sort by pubDate descending (newest first)
    articles.sort(key=lambda x: x.get("pubDate", ""), reverse=True)
    return articles[0]


def mark_article_posted(slug: str):
    """Tandai artikel sudah dipost ke Threads (state file)."""
    state = load_state()
    posted = set(state.get("posted_articles", []))
    posted.add(slug)
    state["posted_articles"] = sorted(posted)
    save_state(state)


def refresh_token() -> dict:
    """Refresh token long-lived Threads (60 hari lagi). Token harus berusia min 24 jam & belum expired."""
    import urllib.request, urllib.parse, urllib.error, json as _json
    from pathlib import Path
    
    env_path = Path("/opt/data/.env")
    current = None
    for line in env_path.read_text().splitlines():
        if line.startswith("THREADS_ACCESS_TOKEN="):
            current = line.split("=", 1)[1]
            break
    if not current:
        return {"success": False, "error": "THREADS_ACCESS_TOKEN tidak ditemukan di .env"}
    
    params = {
        "grant_type": "th_refresh_token",
        "access_token": current,
    }
    url = "https://graph.threads.com/refresh_access_token?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url) as r:
            d = _json.loads(r.read())
            new_token = d.get("access_token")
            if not new_token:
                return {"success": False, "error": f"Tidak ada access_token di respons: {d}"}
            # Update .env
            lines = env_path.read_text().splitlines()
            new_lines = []
            for line in lines:
                if line.startswith("THREADS_ACCESS_TOKEN="):
                    new_lines.append(f"THREADS_ACCESS_TOKEN={new_token}")
                else:
                    new_lines.append(line)
            env_path.write_text("\n".join(new_lines) + "\n")
            return {"success": True, "expires_in": d.get("expires_in")}
    except urllib.error.HTTPError as e:
        return {"success": False, "error": f"HTTP {e.code}: {e.read().decode()[:200]}"}


def count_unposted() -> int:
    """Hitung artikel yang belum dipost ke Threads."""
    posted = set(load_state().get("posted_articles", []))
    content_dir = Path("/opt/data/web-blog-astro/src/content/blog")
    count = 0
    for cat in ["tech", "living"]:
        cat_path = content_dir / cat
        if not cat_path.exists():
            continue
        for md_file in cat_path.glob("*.mdx"):
            content = md_file.read_text(encoding="utf-8")
            if "draft: true" in content:
                continue
            if md_file.stem not in posted:
                count += 1
    return count


def extract_steps(content: str, max_steps: int = 4) -> list:
    """Extract 'Langkah X: ...' headings dari MDX, tampilkan SETENGAH dari total (min 2, maks max_steps)."""
    all_steps = []
    for m in re.finditer(r"^##\s+(Langkah\s+\d+[^:：]*[:：]?\s*[^\n]*)", content, re.MULTILINE):
        raw = m.group(1).strip()
        # Bersihkan markdown bold
        raw = re.sub(r"\*\*(.+?)\*\*", r"\1", raw)
        # Hapus awalan "Langkah N:" biar ringkas
        raw = re.sub(r"^Langkah\s+\d+\s*[:：]?\s*", "", raw).strip()
        # Kapitalisasi huruf pertama
        if raw:
            raw = raw[0].upper() + raw[1:]
            all_steps.append(raw)
    
    if not all_steps:
        return []
    
    # Tampilkan setengah dari total (pembulatan ke atas), minimal 2, maks max_steps
    n = max(2, min(max_steps, -(-len(all_steps) // 2)))
    return all_steps[:n]


def build_threads_post(article: dict, article_content: str = "", include_url: bool = False) -> str:
    """Build a Threads post from article data (hook + steps + link).

    include_url=False (Opsi A): teks post TANPA URL → tidak ada link preview card;
    URL artikel dipindah ke komentar pertama.
    """
    title = article["title"]
    description = article["description"]
    slug = article["slug"]
    category = article["category"]
    
    # Category emoji
    cat_emoji = "⚙️" if category == "tech" else "🏠"
    cat_label = "Teknologi" if category == "tech" else "Kehidupan"
    
    # Article URL — custom domain serve di root, TANPA /blog/
    article_url = f"{BLOG_BASE_URL}/{category}/{slug}/"
    
    # Build hook — pembuka menarik + inti + CTA (tanpa URL kalau include_url=False)
    hook = f"{cat_emoji} {title}\n\n"
    hook += f"{description}\n\n"
    
    # Ringkasan langkah (setengah dari yang ada, maks 4)
    steps = extract_steps(article_content)
    if steps:
        hook += "Beberapa langkahnya:\n"
        for s in steps:
            hook += f"▫️ {s}\n"
        hook += "\n"
    
    if include_url:
        hook += f"👇 Baca panduan lengkapnya di sini:\n{article_url}\n\n"
    else:
        hook += f"👇 Panduan lengkapnya ada di komentar ya!\n\n"
    
    hook += f"Follow @lofaonline buat tips {cat_label} lainnya 🚀"
    
    # Hashtags — WAJIB di baris yang SAMA dengan teks lain (baris baru yang diawali # = heading markdown, #-nya hilang)
    tags_clean = []
    if article.get("tags"):
        tags = [t.strip() for t in article["tags"].strip("[]").split(",")]
        for tag in tags[:4]:
            tag_clean = re.sub(r"[^a-zA-Z0-9]", "", tag)
            if tag_clean:
                tags_clean.append(f"#{tag_clean}")
    
    if tags_clean:
        hook += " " + " ".join(tags_clean) + " ✨"
    
    # Threads API: text maks 500 karakter. Potong otomatis biar tidak error.
    MAX_CHARS = 500
    if len(hook) > MAX_CHARS:
        # Potong dari tengah (bagian langkah), pertahankan judul + deskripsi + CTA + link
        header = f"{cat_emoji} {title}\n\n{description}\n\n"
        footer_start = hook.rfind("👇")
        footer = hook[footer_start:] if footer_start != -1 else ""
        # Sisakan ruang untuk footer + elipsis
        budget = MAX_CHARS - len(footer) - 3
        if budget > len(header):
            hook = header[:budget].rstrip() + "...\n\n" + footer
        else:
            hook = hook[:MAX_CHARS - 3].rstrip() + "..."
    
    return hook


def api_call(method: str, path: str, data: dict | None = None) -> dict:
    """Call Threads API — dengan retry jaringan (3x) untuk error koneksi/network."""
    import time
    url = f"{THREADS_API_BASE}{path}"
    if method == "GET":
        url += "?" + urllib.parse.urlencode(data or {})
        req = urllib.request.Request(url, method="GET")
    else:
        encoded = urllib.parse.urlencode(data or {}).encode("utf-8")
        req = urllib.request.Request(url, data=encoded, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
    
    # Retry 3x khusus error jaringan (Network unreachable, timeout, DNS, dll)
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            # Error HTTP = respon API valid (bukan masalah jaringan) → langsung balik
            return {"error": e.read().decode("utf-8"), "status": e.code}
        except (urllib.error.URLError, OSError, TimeoutError, ConnectionError) as e:
            print(f"   ⏳ Network error attempt {attempt}: {e}... retry")
            if attempt < 3:
                time.sleep(15 * attempt)  # 15s, 30s
    return {"error": f"Network unreachable after 3 attempts", "status": -1}


# --- State tracking komen (maks 3 per post) ---
STATE_FILE = Path("/opt/data/web-blog-astro/.threads_comment_state.json")

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {}

def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2))

def get_affiliate_products() -> list:
    """Ambil semua produk ber-affiliate (nama + URL) dari src/lib/products.ts."""
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
    """Buat teks komen natural & singkat: rekomendasi produk + URL affiliate."""
    name = shorten_product_name(product["name"])
    url = product["url"]
    # Variasi template natural & pendek (bukan pola "Beli di sini")
    texts = [
        f"Btw, buat yang lagi nyari {name}, aku nemu yang bagus dan harganya oke. Cek: {url}",
        f"Btw soal ini, kalau butuh {name} yang worth it, aku rekomen yang ini: {url}",
        f"Ngomong-ngomong, buat yang cari {name}, ini yang aku pakai dan oke banget: {url}",
    ]
    return texts[0]


def shorten_product_name(full_name: str) -> str:
    """Singkatkan nama produk Shopee (yang panjang) jadi nama yang wajar & pendek."""
    name = full_name.strip()
    # Buang bagian 'merek + model' yang panjang: ambil potongan paling deskriptif
    # Contoh: "ZIFRIEND KA646 Mechanical Keyboard RGB Gaming 65% Hot Swap Red/Blue Switch Wired Keyboard"
    # → "keyboard mechanical hot-swap"
    lower = name.lower()
    
    # Pola umum nama produk → deskripsi singkat
    patterns = [
        # (regex untuk deteksi, nama singkat yang dipakai)
        (r"mechanical keyboard.*", "keyboard mechanical"),
        (r"keyboard.*gaming.*", "keyboard gaming"),
        (r"ram laptop", "RAM laptop"),
        (r"kain lap microfiber.*", "kain lap microfiber"),
        (r"kotak penyimpanan.*", "kotak penyimpanan"),
        (r"plastik (zip.?lock|klip).*", "plastik ziplock"),
        (r"food box.*|wadah makanan.*", "wadah makanan kedap udara"),
        (r"storage box.*", "storage box"),
    ]
    for pattern, short in patterns:
        if re.search(pattern, lower):
            return short
    
    # Fallback: ambil 3-4 kata pertama
    words = name.split()
    if len(words) > 5:
        return " ".join(words[:4]).rstrip(",").lower()
    return name.lower()


def get_own_posts(max_posts: int = 10) -> list:
    """Ambil daftar post sendiri dari Threads API."""
    uid = THREADS_USER_ID
    resp = api_call("GET", f"/{uid}/threads", {"fields": "id,text", "access_token": THREADS_ACCESS_TOKEN})
    if "error" in resp:
        return []
    return resp.get("data", [])[:max_posts]


def auto_comment_own_posts(min_posts: int = 1, max_posts: int = 3, comments_per_post: int = 1, dry_run: bool = False) -> dict:
    """Komen otomatis di 1-3 post sendiri (jumlah random), 1 komen per post."""
    import random
    
    posts = get_own_posts()
    if not posts:
        return {"success": False, "error": "Tidak ada post sendiri ditemukan"}
    
    # Pilih random 1-3 post
    n = random.randint(min_posts, min(max_posts, len(posts)))
    random.shuffle(posts)
    chosen_posts = posts[:n]
    
    print(f"📋 {len(posts)} post ditemukan, pilih {n} post random:")
    results = []
    for p in chosen_posts:
        pid = p["id"]
        preview = (p.get("text") or "")[:60].replace("\n", " ")
        print(f"\n📌 Post {pid}: {preview}...")
        r = auto_comment(pid, max_comments=comments_per_post, dry_run=dry_run)
        results.append({"post_id": pid, "result": r})
    
    ok = sum(1 for r in results if r["result"].get("posted", 0) > 0)
    return {"success": ok > 0, "commented": ok, "total": len(results), "results": results}


def post_comment(post_id: str, text: str) -> dict:
    """Komen/balas ke sebuah post via Threads API (dengan retry + jeda)."""
    import time
    uid = THREADS_USER_ID
    
    # Step 1: buat reply container
    create_data = {
        "access_token": THREADS_ACCESS_TOKEN,
        "media_type": "TEXT",
        "text": text,
        "reply_to_id": post_id,
    }
    resp = api_call("POST", f"/{uid}/threads", create_data)
    if "error" in resp:
        return {"success": False, "error": f"Create reply failed: {resp.get('error', resp)}"}
    
    creation_id = resp.get("id")
    if not creation_id:
        return {"success": False, "error": f"No creation_id: {resp}"}
    
    # Jeda singkat biar container siap di server (hindari error 24 "media not found")
    time.sleep(5)
    
    # Step 2: publish (dengan retry 3x — error 24/transient sering hilang setelah jeda)
    publish_data = {
        "access_token": THREADS_ACCESS_TOKEN,
        "creation_id": creation_id,
    }
    for attempt in range(1, 4):
        resp = api_call("POST", f"/{uid}/threads_publish", publish_data)
        if "error" not in resp:
            return {"success": True, "comment_id": resp.get("id")}
        err = str(resp.get("error", ""))
        print(f"   ⏳ Publish attempt {attempt} gagal ({err[:80]}...), retry...")
        time.sleep(8 * attempt)
    
    return {"success": False, "error": f"Publish reply failed after retries: {resp}"}


def auto_comment(post_id: str, max_comments: int = 3, dry_run: bool = False) -> dict:
    """Komen otomatis: maks 3 URL affiliate per post (dengan jeda acak)."""
    state = load_state()
    post_key = f"post_{post_id}"
    already = state.get(post_key, 0)
    
    if already >= max_comments:
        return {"success": False, "error": f"Post {post_id} sudah dapat {already} komen (maks {max_comments})", "already": already}
    
    products = get_affiliate_products()
    if not products:
        return {"success": False, "error": "Tidak ada produk ber-affiliate di products.ts"}
    
    # Pilih produk yang belum pernah dipakai (rotasi)
    used_ids = set(state.get("used_products", []))
    available = [p for p in products if p["id"] not in used_ids]
    if not available:
        available = products  # reset rotasi kalau semua sudah dipakai
    chosen = available[:max_comments - already]
    
    results = []
    used_list = list(used_ids)
    for i, product in enumerate(chosen):
        text = build_comment_text(product)
        print(f"  [{i+1}/{len(chosen)}] Komen: {text[:80]}...")
        if dry_run:
            results.append({"success": True, "dry_run": True, "product": product["name"], "url": product["url"]})
        else:
            r = post_comment(post_id, text)
            results.append(r)
            if r.get("success"):
                used_list.append(product["id"])
                state["used_products"] = used_list
                state[post_key] = already + i + 1
                save_state(state)
                print(f"   ✅ Komen affiliate OK: {r['comment_id']}")
            else:
                # Cetak error asli supaya tidak bingung "tidak ada komen"
                print(f"   ❌ Komen affiliate GAGAL: {r.get('error', r)}")
                # Jeda acak 30-90 detik antar komen (anti-spam)
                if i < len(chosen) - 1:
                    import random, time
                    delay = random.randint(30, 90)
                    print(f"  ⏳ jeda {delay} detik...")
                    time.sleep(delay)
    
    ok = sum(1 for r in results if r.get("success"))
    return {"success": ok > 0, "posted": ok, "total": len(chosen), "results": results}


def refill_bank(auto_generate: bool = True) -> list:
    """Isi ulang bank konten kalau sudah habis. Generate dari artikel blog terbaru."""
    import json as _json
    
    bank_path = Path("/opt/data/web-blog-astro/scripts/threads_content_bank.json")
    if not bank_path.exists():
        return []
    bank = _json.loads(bank_path.read_text(encoding="utf-8"))
    state = load_state()
    used = set(state.get("posted_bank", []))
    
    # Sisa konten yang belum dipost
    available = [item for item in bank if item["id"] not in used]
    if available:
        return available  # masih ada, tidak perlu isi ulang
    
    # Bank habis → generate batch baru dari artikel blog yang ada
    print("📦 Bank konten habis — generate batch baru dari artikel blog...")
    new_items = []
    articles = []
    content_dir = Path("/opt/data/web-blog-astro/src/content/blog")
    for cat in ["tech", "living"]:
        cat_path = content_dir / cat
        if not cat_path.exists():
            continue
        for md_file in cat_path.glob("*.mdx"):
            content = md_file.read_text(encoding="utf-8")
            if "draft: true" in content:
                continue
            fm_match = re.match(r"---\n(.*?)\n---", content, re.DOTALL)
            if not fm_match:
                continue
            fm = {}
            for line in fm_match.group(1).split("\n"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    fm[k.strip()] = v.strip().strip('"')
            articles.append({
                "slug": md_file.stem,
                "category": cat,
                "title": fm.get("title", ""),
                "description": fm.get("description", ""),
                "tags": fm.get("tags", ""),
            })
    
    # Buat tips + pertanyaan dari artikel (versi santai, TANPA frasa kaku)
    for art in articles:
        slug = art["slug"]
        title = art["title"].strip()
        desc = art["description"].strip()
        cat = art["category"]
        
        # Tips: judul + inti (dari description artikel)
        tips_text = f"{title}\n\n{desc[:120]}\n\nbuat yang belum tau, semoga ngebantu ya"
        new_items.append({
            "id": f"tips-{slug}",
            "category": cat,
            "type": "tips",
            "text": tips_text,
        })
        
        # Pertanyaan: hook dari judul, gaya ngobrol
        q_text = f"penasaran sih, ada yang pernah nyoba {title.lower()}? share pengalamannya dong"
        new_items.append({
            "id": f"q-{slug}",
            "category": cat,
            "type": "question",
            "text": q_text,
        })
    
    if not new_items:
        return []
    
    # Simpan batch baru ke bank (gabung dengan bank lama yang sudah dipost, biar state tetap valid)
    merged = bank + new_items
    bank_path.write_text(_json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✅ Bank diisi ulang: {len(new_items)} konten baru (dari {len(articles)} artikel)")
    return new_items


def post_bank_item(dry_run: bool = False) -> dict:
    """Post 1 item random dari bank konten (tips/question) — TANPA komen affiliate.
    
    Alur: pilih item yang belum dipost → post teks → selesai.
    Kalau bank habis, generate otomatis batch baru dari artikel blog.
    """
    import random, json as _json
    
    bank_path = Path("/opt/data/web-blog-astro/scripts/threads_content_bank.json")
    if not bank_path.exists():
        return {"success": False, "error": "threads_content_bank.json tidak ditemukan"}
    
    bank = _json.loads(bank_path.read_text(encoding="utf-8"))
    state = load_state()
    used = set(state.get("posted_bank", []))
    
    # Pilih item random yang belum dipost
    available = [item for item in bank if item["id"] not in used]
    if not available:
        # Bank habis → generate batch baru otomatis
        new_items = refill_bank()
        if not new_items:
            return {"success": False, "error": "Bank habis & tidak bisa generate konten baru"}
        # Ambil dari batch baru
        available = [item for item in bank if item["id"] not in used]
    
    item = random.choice(available)
    print(f"📝 Bank item: {item['id']} ({item['type']}, {item['category']})")
    print(f"   Teks: {item['text'][:80]}...")
    
    if dry_run:
        return {"success": True, "dry_run": True, "item": item}
    
    # Post teks (tanpa URL → tanpa preview card, TANPA komen affiliate)
    post_result = post_to_threads(item["text"])
    if not post_result["success"]:
        return {"success": False, "error": f"Post gagal: {post_result['error']}"}
    post_id = post_result["post_id"]
    print(f"   ✅ Posted! Post ID: {post_id}")
    
    # Tandai sudah dipost
    used.add(item["id"])
    state["posted_bank"] = sorted(used)
    save_state(state)
    
    return {"success": True, "post_id": post_id, "item_id": item["id"]}


def post_article_with_comments(article: dict, article_content: str, dry_run: bool = False) -> dict:
    """Opsi A lengkap: post artikel (tanpa URL) → komen link artikel → jeda 1-5 menit → komen affiliate."""
    import random, time
    
    # 1) Post artikel tanpa URL (biar tidak ada link preview card)
    post_text = build_threads_post(article, article_content, include_url=False)
    print("🚀 1. Post artikel (tanpa URL):")
    print(f"   {post_text[:100]}...")
    
    if dry_run:
        print("   (dry-run, skip posting)")
        return {"success": True, "dry_run": True}
    
    post_result = post_to_threads(post_text)
    if not post_result["success"]:
        return {"success": False, "error": f"Post gagal: {post_result['error']}"}
    post_id = post_result["post_id"]
    print(f"   ✅ Posted! Post ID: {post_id}")
    
    # Tandai artikel sudah dipost ke Threads (anti duplikat)
    mark_article_posted(article["slug"])
    print(f"   📌 Artikel '{article['slug']}' ditandai sudah dipost.")
    
    # 2) Komen link artikel (jeda 30-90 detik dari post)
    delay1 = random.randint(30, 90)
    print(f"⏳ 2. Jeda {delay1} detik, lalu komen link artikel...")
    time.sleep(delay1)
    
    slug = article["slug"]
    category = article["category"]
    article_url = f"{BLOG_BASE_URL}/{category}/{slug}/"
    link_comment = f"📖 Panduan lengkapnya di sini:\n{article_url}"
    r1 = post_comment(post_id, link_comment)
    if r1.get("success"):
        print(f"   ✅ Komen link artikel terposting: {r1['comment_id']}")
    else:
        print(f"   ⚠️ Komen link artikel gagal: {r1.get('error', r1)}")
    
    # 3) Jeda 1-5 menit, lalu komen affiliate
    delay2 = random.randint(60, 300)
    print(f"⏳ 3. Jeda {delay2} detik (1-5 menit), lalu komen affiliate...")
    time.sleep(delay2)
    
    r2 = auto_comment(post_id, max_comments=1, dry_run=False)
    if r2.get("posted", 0) > 0:
        print(f"   ✅ Komen affiliate terposting")
    else:
        print(f"   ⚠️ Komen affiliate: {r2.get('error', 'tidak ada komen')}")
    
    return {"success": True, "post_id": post_id, "link_comment": r1, "affiliate_comment": r2}


def post_to_threads(text: str, image_path: str | None = None) -> dict:
    """Post to Threads via Threads API (graph.threads.net). Dengan retry + jeda."""
    import time
    if not THREADS_ACCESS_TOKEN or not THREADS_USER_ID:
        return {
            "success": False,
            "error": "Missing THREADS_ACCESS_TOKEN or THREADS_USER_ID in .env"
        }
    
    # Step 1: Create media container
    create_data = {
        "access_token": THREADS_ACCESS_TOKEN,
        "media_type": "TEXT",
        "text": text,
    }
    resp = api_call("POST", f"/{THREADS_USER_ID}/threads", create_data)
    
    if "error" in resp:
        return {"success": False, "error": f"Create container failed: {resp.get('error', resp)}"}
    
    creation_id = resp.get("id")
    if not creation_id:
        return {"success": False, "error": f"No creation_id: {resp}"}
    
    # Jeda singkat biar container siap di server (hindari error 24 "media not found")
    time.sleep(5)
    
    # Step 2: Publish the container (dengan retry 3x — error 24/transient sering hilang setelah jeda)
    publish_data = {
        "access_token": THREADS_ACCESS_TOKEN,
        "creation_id": creation_id,
    }
    for attempt in range(1, 4):
        resp = api_call("POST", f"/{THREADS_USER_ID}/threads_publish", publish_data)
        if "error" not in resp:
            return {"success": True, "post_id": resp.get("id")}
        err = str(resp.get("error", ""))
        print(f"   ⏳ Publish attempt {attempt} gagal ({err[:80]}...), retry...")
        time.sleep(8 * attempt)
    
    return {"success": False, "error": f"Publish failed after retries: {resp}"}


def main():
    parser = argparse.ArgumentParser(description="Auto-post blog article to Threads")
    parser.add_argument("--article-slug", help="Specific article slug to post")
    parser.add_argument("--category", choices=["tech", "living"], help="Filter by category")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be posted without posting")
    parser.add_argument("--text", help="Custom text to post (skip article lookup)")
    parser.add_argument("--comment", metavar="POST_ID", help="Auto-comment affiliate URLs on a post (max 3)")
    parser.add_argument("--comment-own", action="store_true", help="Auto-comment on 1-3 random own posts")
    parser.add_argument("--auto", action="store_true", help="Opsi A: post artikel + komen link + jeda + komen affiliate")
    parser.add_argument("--bank", action="store_true", help="Post 1 konten random dari bank (tips/question) + komen affiliate")
    parser.add_argument("--refresh-token", action="store_true", help="Refresh token long-lived Threads (60 hari lagi)")
    parser.add_argument("--max-comments", type=int, default=1, help="Max comments per post (default: 1)")
    args = parser.parse_args()
    
    # Mode refresh token
    if args.refresh_token:
        print("🔄 Refresh token Threads...")
        r = refresh_token()
        if r.get("success"):
            print(f"✅ Token di-refresh! Valid lagi {round(r.get('expires_in', 0)/86400, 1)} hari.")
        else:
            print(f"❌ Gagal: {r.get('error')}")
            sys.exit(1)
        return
    
    # Mode bank konten (tips/pertanyaan random + komen affiliate)
    if args.bank:
        if not THREADS_ACCESS_TOKEN or not THREADS_USER_ID:
            print("❌ THREADS_ACCESS_TOKEN / THREADS_USER_ID belum di-set di .env")
            sys.exit(1)
        print("💬 Mode bank konten...")
        result = post_bank_item(dry_run=args.dry_run)
        if result.get("error"):
            print(f"⚠️ {result['error']}")
            sys.exit(1)
        if args.dry_run:
            print("(dry-run, tidak benar-benar posting)")
        elif result.get("post_id"):
            print(f"✅ Selesai! Post: https://www.threads.net/@lofaonline/post/{result['post_id']}")
        return
    
    # Mode Opsi A: post artikel + komen link + komen affiliate
    if args.auto:
        if not THREADS_ACCESS_TOKEN or not THREADS_USER_ID:
            print("❌ THREADS_ACCESS_TOKEN / THREADS_USER_ID belum di-set di .env")
            sys.exit(1)
        # Ambil artikel
        article_content = ""
        if args.article_slug:
            content_dir = Path("/opt/data/web-blog-astro/src/content/blog")
            found = None
            for cat in ["tech", "living"]:
                md_file = content_dir / cat / f"{args.article_slug}.mdx"
                if md_file.exists():
                    content = md_file.read_text(encoding="utf-8")
                    fm_match = re.match(r"---\n(.*?)\n---", content, re.DOTALL)
                    if fm_match:
                        fm_text = fm_match.group(1)
                        fm = {}
                        for line in fm_text.split("\n"):
                            if ":" in line:
                                key, val = line.split(":", 1)
                                fm[key.strip()] = val.strip().strip('"')
                        found = {
                            "slug": args.article_slug,
                            "category": cat,
                            "title": fm.get("title", ""),
                            "description": fm.get("description", ""),
                            "pubDate": fm.get("pubDate", ""),
                            "tags": fm.get("tags", ""),
                            "cover": fm.get("cover", ""),
                        }
                        article_content = content
                    break
            article = found
        else:
            article = get_latest_article(args.category)
            article_content = ""
            if article:
                md_file = Path("/opt/data/web-blog-astro/src/content/blog") / article["category"] / f"{article['slug']}.mdx"
                if md_file.exists():
                    article_content = md_file.read_text(encoding="utf-8")
        
        if not article:
            # Semua artikel sudah dipost → pesan sukses (cron akan kirim ini ke Telegram)
            print("✅ Semua artikel blog sudah dipost ke Threads. Tidak ada backlog tersisa.")
            return
        
        print(f"📝 Artikel: {article['title']} ({article['category']})")
        result = post_article_with_comments(article, article_content, dry_run=args.dry_run)
        if result.get("error"):
            print(f"❌ {result['error']}")
            sys.exit(1)
        if not args.dry_run and result.get("post_id"):
            sisa = count_unposted()
            print(f"\n✅ Selesai! Post: https://www.threads.net/@lofaonline/post/{result['post_id']}")
            print(f"📊 Sisa backlog: {sisa} artikel belum dipost ke Threads")
        return
    
    # Mode komen otomatis di post sendiri (random 1-3)
    if args.comment_own:
        if not THREADS_ACCESS_TOKEN or not THREADS_USER_ID:
            print("❌ THREADS_ACCESS_TOKEN / THREADS_USER_ID belum di-set di .env")
            sys.exit(1)
        print("💬 Auto-comment di 1-3 post sendiri (random)...")
        result = auto_comment_own_posts(min_posts=1, max_posts=3, comments_per_post=args.max_comments, dry_run=args.dry_run)
        if result.get("error"):
            print(f"⚠️ {result['error']}")
        print(f"✅ Post dikomen: {result.get('commented', 0)}/{result.get('total', 0)}")
        if args.dry_run:
            print("(dry-run, tidak benar-benar komen)")
        return
    
    # Mode komen ke post tertentu
    if args.comment:
        if not THREADS_ACCESS_TOKEN or not THREADS_USER_ID:
            print("❌ THREADS_ACCESS_TOKEN / THREADS_USER_ID belum di-set di .env")
            sys.exit(1)
        print(f"💬 Auto-comment ke post {args.comment} (maks {args.max_comments} komen)...")
        result = auto_comment(args.comment, max_comments=args.max_comments, dry_run=args.dry_run)
        if result.get("error"):
            print(f"⚠️ {result['error']}")
        print(f"✅ Komen terposting: {result.get('posted', 0)}/{result.get('total', 0)}")
        if args.dry_run:
            print("(dry-run, tidak benar-benar komen)")
        return
    
    # Custom text mode
    if args.text:
        post_text = args.text
        print("📝 Custom text mode")
    else:
        # Get article
        if args.article_slug:
            content_dir = Path("/opt/data/web-blog-astro/src/content/blog")
            found = None
            for cat in ["tech", "living"]:
                md_file = content_dir / cat / f"{args.article_slug}.mdx"
                if md_file.exists():
                    content = md_file.read_text(encoding="utf-8")
                    fm_match = re.match(r"---\n(.*?)\n---", content, re.DOTALL)
                    if fm_match:
                        fm_text = fm_match.group(1)
                        fm = {}
                        for line in fm_text.split("\n"):
                            if ":" in line:
                                key, val = line.split(":", 1)
                                fm[key.strip()] = val.strip().strip('"')
                        found = {
                            "slug": args.article_slug,
                            "category": cat,
                            "title": fm.get("title", ""),
                            "description": fm.get("description", ""),
                            "pubDate": fm.get("pubDate", ""),
                            "tags": fm.get("tags", ""),
                            "cover": fm.get("cover", ""),
                        }
                    break
            article = found
        else:
            article = get_latest_article(args.category)
        
        if not article:
            print("❌ No article found")
            sys.exit(1)
        
        print(f"📝 Article: {article['title']}")
        print(f"📂 Category: {article['category']}")
        print(f"🔗 Slug: {article['slug']}")
        
        # Baca konten artikel (untuk ekstrak langkah)
        article_content = ""
        content_dir = Path("/opt/data/web-blog-astro/src/content/blog")
        md_file = content_dir / article["category"] / f"{article['slug']}.mdx"
        if md_file.exists():
            article_content = md_file.read_text(encoding="utf-8")
        
        # Build post
        post_text = build_threads_post(article, article_content)
    
    print("\n--- POST PREVIEW ---")
    print(post_text)
    print("--- END PREVIEW ---\n")
    
    if args.dry_run:
        print("✅ Dry run complete - not posting")
        return
    
    if not THREADS_ACCESS_TOKEN or not THREADS_USER_ID:
        print("❌ THREADS_ACCESS_TOKEN / THREADS_USER_ID belum di-set di .env")
        sys.exit(1)
    
    # Post to Threads
    print("🚀 Posting to Threads...")
    result = post_to_threads(post_text)
    
    if result["success"]:
        print(f"✅ Posted! Post ID: {result['post_id']}")
        print(f"🔗 https://www.threads.net/@{os.getenv('THREADS_USERNAME', 'user')}/post/{result['post_id']}")
    else:
        print(f"❌ Failed: {result['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()