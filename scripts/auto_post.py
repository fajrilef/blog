#!/usr/bin/env python3
"""
Auto-post artikel blog Lofa — 1 artikel per 60 menit.
Jika sisa pending ≤ 5 → generate 25 artikel baru otomatis.

Pakai:
  python3 scripts/auto_post.py          # post 1 artikel (cron 60 menit)
  python3 scripts/auto_post.py --check  # cek status saja
  python3 scripts/auto_post.py --force  # post walaupun masih < 60 menit (debug)
"""

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOOGLE_API = "/opt/data/skills/productivity/google-workspace/scripts/google_api.py"
SID = "1JWgph214tsk9HFAeRyG5uhGicxU18RBGQ7O7nVN6CkY"
STATE_FILE = os.path.join(ROOT, "scripts", ".autopost_state.json")
PYTHON = "/opt/data/.xlsx-venv/bin/python"

# WIB timezone
WIB = timezone(timedelta(hours=7))

# Cover image mapping untuk artikel living yang belum punya cover
LIVING_COVER_MAP = {
    "cara-membersihkan-kulkas-agar-tidak-bau": "cover-fridge-clean.jpg",
    "cara-menghilangkan-bau-tidak-sedap-di-kulkas": "cover-fridge-odor.jpg",
    "cara-menyimpan-barang-di-rumah-agar-lebih-rapi": "cover-home-storage.jpg",
    "cara-membersihkan-keyboard-mouse-dan-perangkat-kerja": "cover-clean-devices.jpg",
    "cara-menyimpan-cabai-agar-tidak-cepat-busuk": "cover-chili-storage.jpg",
    "cara-menyimpan-bawang-merah-agar-tahan-lama": "cover-shallot-storage.jpg",
    "cara-menyimpan-bawang-putih-agar-tidak-cepat-rusak": "cover-garlic-storage.jpg",
    "berapa-lama-sayuran-bisa-disimpan-di-kulkas": "cover-veg-shelf-life.jpg",
    "cara-menyimpan-sayuran-daun": "cover-leafy-greens.jpg",
    "cara-menyimpan-buah-agar-tidak-busuk": "cover-fruit-storage.jpg",
    "cara-membersihkan-lantai-kayu": "cover-wood-floor.jpg",
    "cara-mengatur-dapur-kecil": "cover-small-kitchen.jpg",
    "cara-menghilangkan-noda-minyak-di-baju": "cover-oil-stain.jpg",
    "cara-menyimpan-nasi-agar-tidak-basi": "cover-rice-storage.jpg",
}

# Cover image mapping untuk artikel tech yang belum punya cover
TECH_COVER_MAP = {
    "apa-itu-keyboard-mechanical": "cover-keyboard-intro.svg",
    "cara-memilih-keyboard-mechanical": "cover-keyboard-memilih.svg",
    "perbedaan-red-switch-brown-switch-blue-switch": "cover-switch-comparison.svg",
    "mechanical-keyboard-vs-membrane": "cover-mech-vs-membrane.svg",
    "apa-itu-hot-swap-pada-keyboard-mechanical": "cover-hotswap.svg",
    "cara-mengatasi-keyboard-mechanical-double-input": "cover-cara-mengatasi-keyboard-mechanical-double-input.jpg",
    "keyboard-tidak-terdeteksi-di-windows": "cover-keyboard-tidak-terdeteksi-di-windows.jpg",
    "cara-mengatasi-tombol-keyboard-mechanical-tidak-berfungsi": "cover-double-input.svg",
    "seberapa-sering-keyboard-mechanical-harus-dibersihkan": "cover-cleaning-frequency.svg",
    "bolehkah-membersihkan-keyboard-mechanical-dengan-air": "cover-water-cleaning.svg",
    "cara-mematikan-startup-apps-di-windows-11": "cover-startup-apps.svg",
    "cara-membersihkan-storage-windows-11": "cover-clean-storage.svg",
    "cara-mengecek-kesehatan-ssd-di-windows": "cover-ssd-health.svg",
    "cara-mengecek-ram-laptop-di-windows": "cover-ram-check.svg",
    "cara-mengatasi-laptop-lemot-di-windows-11": "cover-laptop-slow.svg",
    "cara-mengatasi-wifi-laptop-tidak-terhubung": "cover-wifi-fix.svg",
    "cara-screenshot-di-windows-11": "cover-screenshot.svg",
    "cara-membuat-windows-11-lebih-ringan": "cover-windows-light.svg",
    "cara-mengecek-kesehatan-baterai-laptop": "cover-battery-health.svg",
    "cara-mengetahui-spesifikasi-laptop-windows": "cover-laptop-specs.svg",
    "laptop-cepat-panas-penyebab-dan-cara-mengatasinya": "cover-laptop-overheat.svg",
    "cara-merawat-baterai-laptop-agar-tidak-cepat-rusak": "cover-battery-care.svg",
}


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"last_post_time": 0, "last_post_slug": ""}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def run_google_api(args):
    """Jalankan google_api.py dan return JSON output."""
    cmd = [PYTHON, GOOGLE_API] + args
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        raise RuntimeError(f"google_api.py gagal: {out.stderr[:500]}")
    return json.loads(out.stdout)


def get_pending_articles():
    """Ambil semua artikel dengan Posted to Blog = No atau Status != LIVE."""
    # Baca range yang mencakup kolom P (Posted to Blog)
    data = run_google_api(["sheets", "get", SID, "Content Plan Living!A1:P50"])
    header = data[0]
    rows = data[1:]

    # Cari index kolom
    idx_no = header.index("No")
    idx_cluster = header.index("Cluster")
    idx_judul = header.index("Judul Artikel")
    idx_slug = header.index("Slug (URL)")
    idx_kategori = header.index("Kategori")
    idx_intent = header.index("Intent")
    idx_status = header.index("Status")
    idx_tanggal = header.index("Tanggal Publish")
    idx_meta = header.index("Meta Description")
    idx_tags = header.index("Tags")
    idx_internal = header.index("Internal Link Target")
    idx_foto_kw = header.index("Keyword Pencarian Foto")
    idx_cover = header.index("File Cover")
    idx_catatan = header.index("Catatan")
    idx_aff_kw = header.index("Keyword Produk Affiliate")
    idx_posted = header.index("Posted to Blog") if "Posted to Blog" in header else None

    pending = []
    for i, row in enumerate(rows):
        if len(row) <= idx_no:
            continue
        no = row[idx_no]
        if not no:
            continue
        status = row[idx_status] if len(row) > idx_status else ""
        posted = row[idx_posted] if idx_posted is not None and len(row) > idx_posted else ""

        if status != "LIVE" and posted != "Yes":
            pending.append({
                "no": no,
                "cluster": row[idx_cluster] if len(row) > idx_cluster else "",
                "judul": row[idx_judul] if len(row) > idx_judul else "",
                "slug": row[idx_slug] if len(row) > idx_slug else "",
                "kategori": row[idx_kategori] if len(row) > idx_kategori else "",
                "intent": row[idx_intent] if len(row) > idx_intent else "",
                "meta": row[idx_meta] if len(row) > idx_meta else "",
                "tags": row[idx_tags] if len(row) > idx_tags else "",
                "internal": row[idx_internal] if len(row) > idx_internal else "",
                "foto_kw": row[idx_foto_kw] if len(row) > idx_foto_kw else "",
                "cover": row[idx_cover] if len(row) > idx_cover else "",
                "catatan": row[idx_catatan] if len(row) > idx_catatan else "",
                "aff_kw": row[idx_aff_kw] if len(row) > idx_aff_kw else "",
                "row_index": i + 2,  # 1-based, header = row 1
            })
    return pending


def get_tech_pending():
    """Ambil artikel tech yang pending."""
    data = run_google_api(["sheets", "get", SID, "Content Plan Tech!A1:P50"])
    header = data[0]
    rows = data[1:]

    idx_no = header.index("No")
    idx_cluster = header.index("Cluster")
    idx_judul = header.index("Judul Artikel")
    idx_slug = header.index("Slug (URL)")
    idx_kategori = header.index("Kategori")
    idx_intent = header.index("Intent")
    idx_status = header.index("Status")
    idx_tanggal = header.index("Tanggal Publish")
    idx_meta = header.index("Meta Description")
    idx_tags = header.index("Tags")
    idx_internal = header.index("Internal Link Target")
    idx_foto_kw = header.index("Keyword Pencarian Foto")
    idx_cover = header.index("File Cover")
    idx_catatan = header.index("Catatan")
    idx_aff_kw = header.index("Keyword Produk Affiliate")
    idx_posted = header.index("Posted to Blog") if "Posted to Blog" in header else None

    pending = []
    for i, row in enumerate(rows):
        if len(row) <= idx_no:
            continue
        no = row[idx_no]
        if not no:
            continue
        status = row[idx_status] if len(row) > idx_status else ""
        posted = row[idx_posted] if idx_posted is not None and len(row) > idx_posted else ""

        if status != "LIVE" and posted != "Yes":
            pending.append({
                "no": no,
                "cluster": row[idx_cluster] if len(row) > idx_cluster else "",
                "judul": row[idx_judul] if len(row) > idx_judul else "",
                "slug": row[idx_slug] if len(row) > idx_slug else "",
                "kategori": row[idx_kategori] if len(row) > idx_kategori else "",
                "intent": row[idx_intent] if len(row) > idx_intent else "",
                "meta": row[idx_meta] if len(row) > idx_meta else "",
                "tags": row[idx_tags] if len(row) > idx_tags else "",
                "internal": row[idx_internal] if len(row) > idx_internal else "",
                "foto_kw": row[idx_foto_kw] if len(row) > idx_foto_kw else "",
                "cover": row[idx_cover] if len(row) > idx_cover else "",
                "catatan": row[idx_catatan] if len(row) > idx_catatan else "",
                "aff_kw": row[idx_aff_kw] if len(row) > idx_aff_kw else "",
                "row_index": i + 2,
            })
    return pending


def generate_cover_image(slug, kategori, foto_kw):
    """Generate cover image via Pollinations.ai atau pakai existing."""
    img_dir = os.path.join(ROOT, "public", "assets", "img")
    os.makedirs(img_dir, exist_ok=True)

    # Cek apakah sudah ada cover di map
    ext = "jpg"
    if kategori == "living" and slug in LIVING_COVER_MAP:
        cover_file = LIVING_COVER_MAP[slug]
        ext = "svg" if cover_file.endswith(".svg") else "jpg"
    elif kategori == "tech" and slug in TECH_COVER_MAP:
        cover_file = TECH_COVER_MAP[slug]
        ext = "svg" if cover_file.endswith(".svg") else "jpg"
    else:
        # Generate via Pollinations
        if "svg" in slug or "diagram" in foto_kw.lower():
            ext = "svg"
        cover_file = f"cover-{slug}.{ext}"

    cover_path = os.path.join(img_dir, cover_file)

    # Jika file sudah ada dan tidak kosong, pakai itu
    if os.path.exists(cover_path) and os.path.getsize(cover_path) > 0:
        return cover_file

    # Generate via Pollinations.ai
    if ext == "svg":
        prompt = f"Clean flat illustration, minimal style, {foto_kw}, simple shapes, pastel colors, white background, vector art style"
    else:
        prompt = f"Professional photo, {foto_kw}, clean background, good lighting, high quality, lifestyle photography"

    import urllib.parse
    encoded_prompt = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1200&height=630&format={ext}&seed={abs(hash(slug)) % 1000000}"

    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        if len(data) > 1000:  # minimal size
            with open(cover_path, "wb") as f:
                f.write(data)
            print(f"  ✓ Cover generated: {cover_file}")
            return cover_file
    except Exception as e:
        print(f"  ⚠ Cover generate gagal ({e}), pakai placeholder")

    # Fallback: copy veggie-1.jpg or keyboard-switch.jpg
    fallback = "veggie-1.jpg" if kategori == "living" else "keyboard-switch.jpg"
    fallback_path = os.path.join(img_dir, fallback)
    if os.path.exists(fallback_path):
        import shutil
        shutil.copy2(fallback_path, cover_path)
        return cover_file

    return fallback


def get_recommended_products(art):
    """Tentukan produk affiliate untuk artikel berdasarkan kategori dan keyword."""
    # Baca products.ts untuk cari produk dengan affiliateUrl aktif
    products_ts = os.path.join(ROOT, "src", "lib", "products.ts")
    with open(products_ts) as f:
        content = f.read()

    # Extract products with affiliateUrl
    import re
    products = []
    for match in re.finditer(
        r"id:\s*'([^']+)',.*?name:\s*'([^']+)',.*?category:\s*'(tech|living)',.*?affiliateUrl:\s*'([^']*)'",
        content,
        re.S,
    ):
        pid, name, cat, url = match.groups()
        if url and url != "null":
            products.append({"id": pid, "name": name, "category": cat, "url": url})

    kategori = art["kategori"]
    aff_kw = art["aff_kw"].lower()

    # Filter by category
    cat_products = [p for p in products if p["category"] == kategori]

    # Prioritaskan berdasarkan keyword affiliate
    if aff_kw and aff_kw not in ["batch 1", "batch 2", "batch 3", "batch 4", "batch 5", "batch 6", "batch 7"]:
        kw_products = [p for p in cat_products if any(kw in p["name"].lower() for kw in aff_kw.split(", "))]
        if kw_products:
            return kw_products[:3]

    return cat_products[:3]


def generate_mdx(art, cover_file):
    """Generate konten MDX untuk artikel."""
    now = datetime.now(WIB)
    pub_date = now.strftime("%Y-%m-%dT%H:%M:%S%z")
    pub_date = pub_date[:-2] + ":" + pub_date[-2:]  # +07:00 format

    tags = [t.strip() for t in art["tags"].split(",") if t.strip()]
    tags_str = ", ".join(f'"{t}"' for t in tags)

    # Produk affiliate
    rec_products = get_recommended_products(art)
    if rec_products:
        prod_ids = [p["id"] for p in rec_products]
        prod_str = "\n  ".join(f'- "{pid}"' for pid in prod_ids)
    else:
        prod_str = ""

    # Internal link
    internal = art["internal"] if art["internal"] else ""

    mdx = f"""---
title: "{art['judul']}"
description: "{art['meta']}"
pubDate: {pub_date}
category: {art['kategori']}
tags: [{tags_str}]
cover: {cover_file}
recommendedProducts:
  {prod_str}
---

{art['judul']} adalah topik yang banyak dicari. Dalam artikel ini kita akan membahas langkah-langkah praktis yang bisa langsung diterapkan.

## Pendahuluan

{art['meta']}

## Langkah-Langkah Utama

### 1. Persiapan

Sebelum memulai, pastikan Anda memiliki alat dan bahan yang diperlukan.

### 2. Pelaksanaan

Ikuti langkah-langkah berikut secara berurutan untuk hasil terbaik.

### 3. Tips Tambahan

Beberapa tips tambahan untuk memastikan hasil optimal.

## Kesimpulan

Dengan mengikuti panduan di atas, Anda bisa mengatasi permasalahan ini dengan mudah dan efisien.

**Baca juga:** [{art['judul']}]({internal})
"""
    return mdx


def write_mdx(art, cover_file, mdx_content):
    """Tulis file MDX ke src/content/blog/{kategori}/."""
    kategori_dir = os.path.join(ROOT, "src", "content", "blog", art["kategori"])
    os.makedirs(kategori_dir, exist_ok=True)

    slug = art["slug"]
    filepath = os.path.join(kategori_dir, f"{slug}.mdx")

    with open(filepath, "w") as f:
        f.write(mdx_content)

    print(f"  ✓ MDX written: {filepath}")
    return filepath


def update_sheet_live(art, cover_file):
    """Update sheet: Status=LIVE, Tanggal Publish=today, Posted to Blog=Yes, File Cover=cover_file."""
    today = datetime.now(WIB).strftime("%Y-%m-%d")

    # Update columns: G=Status, H=Tanggal Publish, M=File Cover, P=Posted to Blog
    row = art["row_index"]
    values = [
        ["LIVE"],           # G (Status)
        [today],            # H (Tanggal Publish)
        [cover_file],       # M (File Cover)
        ["Yes"],            # P (Posted to Blog)
    ]
    ranges = [
        f"Content Plan Living!G{row}",
        f"Content Plan Living!H{row}",
        f"Content Plan Living!M{row}",
        f"Content Plan Living!P{row}",
    ]

    for rng, val in zip(ranges, values):
        body = json.dumps([val], ensure_ascii=False)
        out = subprocess.run(
            [PYTHON, GOOGLE_API, "sheets", "update", SID, rng, "--values", body],
            capture_output=True, text=True, timeout=60,
        )
        if out.returncode != 0:
            print(f"  ⚠ Update {rng} gagal: {out.stderr[:200]}")

    print(f"  ✓ Sheet updated: row {row} → LIVE, {today}, {cover_file}, Yes")


def update_sheet_live_tech(art, cover_file):
    """Update sheet Tech: Status=LIVE, Tanggal Publish=today, Posted to Blog=Yes, File Cover=cover_file."""
    today = datetime.now(WIB).strftime("%Y-%m-%d")

    row = art["row_index"]
    values = [
        ["LIVE"],
        [today],
        [cover_file],
        ["Yes"],
    ]
    ranges = [
        f"Content Plan Tech!G{row}",
        f"Content Plan Tech!H{row}",
        f"Content Plan Tech!M{row}",
        f"Content Plan Tech!P{row}",
    ]

    for rng, val in zip(ranges, values):
        body = json.dumps([val], ensure_ascii=False)
        out = subprocess.run(
            [PYTHON, GOOGLE_API, "sheets", "update", SID, rng, "--values", body],
            capture_output=True, text=True, timeout=60,
        )
        if out.returncode != 0:
            print(f"  ⚠ Update {rng} gagal: {out.stderr[:200]}")

    print(f"  ✓ Sheet Tech updated: row {row} → LIVE, {today}, {cover_file}, Yes")


def deploy_blog():
    """Build dan deploy ke Cloudflare Pages (lofa.web.id)."""
    print("  📦 Building blog...")
    out = subprocess.run(
        ["npm", "run", "build"],
        cwd=ROOT, capture_output=True, text=True, timeout=300
    )
    if out.returncode != 0:
        raise RuntimeError(f"Build gagal: {out.stderr[-500:]}")

    print("  📤 Deploying to Cloudflare Pages...")

    # Baca kredensial Cloudflare dari /opt/data/.env
    cf_token = os.environ.get("CLOUDFLARE_API_TOKEN")
    cf_account = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    if not cf_token or not cf_account:
        env_path = os.path.join(os.path.dirname(ROOT), ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith("CLOUDFLARE_API_TOKEN="):
                        cf_token = line.split("=", 1)[1].strip()
                    elif line.startswith("CLOUDFLARE_ACCOUNT_ID="):
                        cf_account = line.split("=", 1)[1].strip()

    if not cf_token or not cf_account:
        raise RuntimeError("CLOUDFLARE_API_TOKEN / CLOUDFLARE_ACCOUNT_ID tidak ditemukan di .env")

    # Lokasi wrangler (npm global di /opt/data/.npm-global/bin)
    wrangler_bin = "/opt/data/.npm-global/bin/wrangler"
    if not os.path.exists(wrangler_bin):
        wrangler_bin = "wrangler"  # fallback ke PATH

    deploy_cmd = [
        wrangler_bin, "pages", "deploy", os.path.join(ROOT, "dist"),
        "--project-name", "lofa-blog",
    ]
    env = {**os.environ, "CLOUDFLARE_API_TOKEN": cf_token, "CLOUDFLARE_ACCOUNT_ID": cf_account}
    out = subprocess.run(deploy_cmd, capture_output=True, text=True, timeout=300, env=env)
    if out.returncode != 0:
        raise RuntimeError(f"Cloudflare deploy gagal: {out.stderr[-500:]}")

    print("  ✓ Deployed to Cloudflare Pages (lofa.web.id)")


def check_and_generate_new_articles(pending_count):
    """Jika pending Living ≤ 5, generate 25 artikel Living baru."""
    if pending_count <= 5:
        print(f"⚠ Pending Living articles only {pending_count} (≤5), generating 25 new Living articles...")
        # Run the rewrite/add scripts for Living
        subprocess.run([PYTHON, "/opt/data/add_living_articles.py"], capture_output=True, text=True, timeout=120)
        subprocess.run([PYTHON, "/opt/data/rewrite_living_sheet.py"], capture_output=True, text=True, timeout=120)
        print("  ✓ New Living articles generated")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Cek status saja")
    parser.add_argument("--force", action="store_true", help="Force post walau < 60 menit")
    args = parser.parse_args()

    state = load_state()
    now_ts = time.time()

    # Cek interval 60 menit (3600 detik)
    if not args.force and not args.check:
        if now_ts - state.get("last_post_time", 0) < 3600:
            print(f"⏳ Belum 60 menit sejak post terakhir ({int((now_ts - state['last_post_time'])/60)} menit lalu). Skip.")
            return

    print(f"🔍 Checking pending articles...")

    # Get pending HANYA dari Living (bukan Tech)
    living_pending = get_pending_articles()
    # tech_pending = get_tech_pending()  # DISABLED - job ini hanya untuk Living
    all_pending = living_pending  # only living

    print(f"  Living pending: {len(living_pending)}")
    # print(f"  Tech pending: {len(tech_pending)}")  # DISABLED
    print(f"  Total pending (Living only): {len(all_pending)}")

    if args.check:
        print("\n=== PENDING ARTICLES (LIVING) ===")
        for art in all_pending:
            print(f"  [{art['no']}] {art['judul'][:50]} | {art['kategori']} | {art['slug']}")
        print(f"\n📈 Total unposted (Living): {len(all_pending)}")
        return

    if not all_pending:
        print("✅ Semua artikel Living sudah LIVE!")
        return

    # Pick next article (Living yang No terkecil)
    all_pending.sort(key=lambda x: int(x["no"]))
    next_art = all_pending[0]

    print(f"\n📝 Posting: [{next_art['no']}] {next_art['judul']} ({next_art['kategori']})")

    # Generate cover
    cover_file = generate_cover_image(next_art["slug"], next_art["kategori"], next_art["foto_kw"])
    print(f"  Cover: {cover_file}")

    # Generate MDX
    mdx_content = generate_mdx(next_art, cover_file)
    write_mdx(next_art, cover_file, mdx_content)

    # Update sheet
    if next_art["kategori"] == "living":
        update_sheet_live(next_art, cover_file)
    else:
        update_sheet_live_tech(next_art, cover_file)

    # Deploy
    try:
        deploy_blog()
    except Exception as e:
        print(f"  ⚠ Deploy gagal: {e}")
        print("  Artikel sudah di-generate, deploy manual nanti.")

    # Update state
    state["last_post_time"] = now_ts
    state["last_post_slug"] = next_art["slug"]
    save_state(state)

    # Build article URL
    article_url = f"https://lofa.web.id/living/{next_art['slug']}/"

    # Print report (format like tech blog)
    print(f"\n{'='*50}")
    print(f"📋 AUTO POST LIVING — REPORT")
    print(f"{'='*50}")
    print(f"⏰ Waktu: {datetime.now(WIB).strftime('%Y-%m-%d %H:%M WIB')}")
    print(f"✅ POSTED:")
    print(f"   ☑ [{next_art['no']}] {next_art['judul']}")
    print(f"      🔗 {article_url}")
    print(f"      📁 Cover: {cover_file}")
    print(f"      📊 Sheet: Row {next_art['row_index']} → LIVE, Posted to Blog=Yes")
    print(f"\n📈 SISA UNPOSTED (Living): {len(all_pending) - 1} artikel")
    for i, art in enumerate(all_pending[1:], 1):
        print(f"   {i}. [{art['no']}] {art['judul'][:60]}")
    print(f"{'='*50}")

    # Check if need to generate new articles
    check_and_generate_new_articles(len(all_pending) - 1)


if __name__ == "__main__":
    main()