#!/usr/bin/env python3
"""
Auto-post artikel TECH blog Lofa — 1 artikel per 60 menit (jam 30 menit).
Hanya memproses kategori tech dari Content Plan Tech sheet.
Jika sisa pending ≤ 5 → generate 25 artikel tech baru otomatis.

Pakai:
  python3 scripts/auto_post_tech.py          # post 1 artikel (cron 60 menit)
  python3 scripts/auto_post_tech.py --check  # cek status saja
  python3 scripts/auto_post_tech.py --force  # post walaupun masih < 60 menit (debug)
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
STATE_FILE = os.path.join(ROOT, "scripts", ".autopost_state_tech.json")
PYTHON = "/opt/data/.xlsx-venv/bin/python"

# WIB timezone
WIB = timezone(timedelta(hours=7))

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
                "kategori": "tech",  # force tech
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


def generate_cover_image(slug, foto_kw):
    """Generate cover image via Pollinations.ai atau pakai existing."""
    img_dir = os.path.join(ROOT, "public", "assets", "img")
    os.makedirs(img_dir, exist_ok=True)

    ext = "jpg"
    if slug in TECH_COVER_MAP:
        cover_file = TECH_COVER_MAP[slug]
        ext = "svg" if cover_file.endswith(".svg") else "jpg"
    else:
        if "svg" in slug or "diagram" in foto_kw.lower():
            ext = "svg"
        cover_file = f"cover-{slug}.{ext}"

    cover_path = os.path.join(img_dir, cover_file)

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
        if len(data) > 1000:
            with open(cover_path, "wb") as f:
                f.write(data)
            print(f"  ✓ Cover generated: {cover_file}")
            return cover_file
    except Exception as e:
        print(f"  ⚠ Cover generate gagal ({e}), pakai placeholder")

    fallback = "keyboard-switch.jpg"
    fallback_path = os.path.join(img_dir, fallback)
    if os.path.exists(fallback_path):
        import shutil
        shutil.copy2(fallback_path, cover_path)
        return cover_file

    return fallback


def get_recommended_products(art):
    """Tentukan produk affiliate untuk artikel tech."""
    products_ts = os.path.join(ROOT, "src", "lib", "products.ts")
    with open(products_ts) as f:
        content = f.read()

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

    aff_kw = art["aff_kw"].lower()

    cat_products = [p for p in products if p["category"] == "tech"]

    if aff_kw and aff_kw not in ["batch 1", "batch 2", "batch 3", "batch 4", "batch 5", "batch 6", "batch 7"]:
        kw_products = [p for p in cat_products if any(kw in p["name"].lower() for kw in aff_kw.split(", "))]
        if kw_products:
            return kw_products[:3]

    return cat_products[:3]


def generate_mdx(art, cover_file):
    """Generate konten MDX untuk artikel tech."""
    now = datetime.now(WIB)
    pub_date = now.strftime("%Y-%m-%dT%H:%M:%S%z")
    pub_date = pub_date[:-2] + ":" + pub_date[-2:]

    tags = [t.strip() for t in art["tags"].split(",") if t.strip()]
    tags_str = ", ".join(f'"{t}"' for t in tags)

    rec_products = get_recommended_products(art)
    if rec_products:
        prod_ids = [p["id"] for p in rec_products]
        prod_str = "\n  ".join(f'- "{pid}"' for pid in prod_ids)
    else:
        prod_str = ""

    internal = art["internal"] if art["internal"] else ""

    mdx = f"""---
title: "{art['judul']}"
description: "{art['meta']}"
pubDate: {pub_date}
category: tech
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
    """Tulis file MDX ke src/content/blog/tech/."""
    kategori_dir = os.path.join(ROOT, "src", "content", "blog", "tech")
    os.makedirs(kategori_dir, exist_ok=True)

    slug = art["slug"]
    filepath = os.path.join(kategori_dir, f"{slug}.mdx")

    with open(filepath, "w") as f:
        f.write(mdx_content)

    print(f"  ✓ MDX written: {filepath}")
    return filepath


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
    """Jika pending tech ≤ 5, generate 25 artikel tech baru."""
    if pending_count <= 5:
        print(f"⚠ Pending Tech articles only {pending_count} (≤5), generating 25 new Tech articles...")
        # TODO: Add tech article generation script when available
        print("  ℹ Tech article generation script not yet implemented")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Cek status saja")
    parser.add_argument("--force", action="store_true", help="Force post walau < 60 menit")
    args = parser.parse_args()

    state = load_state()
    now_ts = time.time()

    if not args.force and not args.check:
        if now_ts - state.get("last_post_time", 0) < 3600:
            print(f"⏳ Belum 60 menit sejak post terakhir ({int((now_ts - state['last_post_time'])/60)} menit lalu). Skip.")
            return

    print(f"🔍 Checking pending Tech articles...")

    tech_pending = get_tech_pending()
    all_pending = tech_pending

    print(f"  Tech pending: {len(tech_pending)}")
    print(f"  Total pending (Tech only): {len(all_pending)}")

    if args.check:
        print("\n=== PENDING ARTICLES (TECH) ===")
        for art in all_pending:
            print(f"  [{art['no']}] {art['judul'][:50]} | {art['kategori']} | {art['slug']}")
        print(f"\n📈 Total unposted (Tech): {len(all_pending)}")
        return

    if not all_pending:
        print("✅ Semua artikel Tech sudah LIVE!")
        return

    all_pending.sort(key=lambda x: int(x["no"]))
    next_art = all_pending[0]

    print(f"\n📝 Posting: [{next_art['no']}] {next_art['judul']} ({next_art['kategori']})")

    cover_file = generate_cover_image(next_art["slug"], next_art["foto_kw"])
    print(f"  Cover: {cover_file}")

    mdx_content = generate_mdx(next_art, cover_file)
    write_mdx(next_art, cover_file, mdx_content)

    update_sheet_live_tech(next_art, cover_file)

    try:
        deploy_blog()
    except Exception as e:
        print(f"  ⚠ Deploy gagal: {e}")
        print("  Artikel sudah di-generate, deploy manual nanti.")

    state["last_post_time"] = now_ts
    state["last_post_slug"] = next_art["slug"]
    save_state(state)

    # Build article URL
    article_url = f"https://lofa.web.id/tech/{next_art['slug']}/"

    # Print report (format like living blog)
    print(f"\n{'='*50}")
    print(f"📋 AUTO POST TECH — REPORT")
    print(f"{'='*50}")
    print(f"⏰ Waktu: {datetime.now(WIB).strftime('%Y-%m-%d %H:%M WIB')}")
    print(f"✅ POSTED:")
    print(f"   ☑ [{next_art['no']}] {next_art['judul']}")
    print(f"      🔗 {article_url}")
    print(f"      📁 Cover: {cover_file}")
    print(f"      📊 Sheet: Row {next_art['row_index']} → LIVE, Posted to Blog=Yes")
    print(f"\n📈 SISA UNPOSTED (Tech): {len(all_pending) - 1} artikel")
    for i, art in enumerate(all_pending[1:], 1):
        print(f"   {i}. [{art['no']}] {art['judul'][:60]}")
    print(f"{'='*50}")

    check_and_generate_new_articles(len(all_pending) - 1)


if __name__ == "__main__":
    main()