#!/usr/bin/env python3
"""
Sync produk affiliate Lofa — otomatis dari Google Sheets "Produk Affiliate".

Alur:
1. Baca sheet "Produk Affiliate" (google_api.py OAuth, token di /opt/data).
2. Untuk tiap baris dengan URL affiliate:
   a. resolve short link s.shopee.co.id → URL produk (HEAD redirect, BUKAN scrape)
   b. parse shop_id + item_id
   c. kalau SHOPEE_APP_ID/SECRET tersedia → fetch foto+judul via Shopee Affiliate Open API
   d. kalau tidak → simpan item_id/shop_id saja (name/image tetap dari products.ts existing, affiliateUrl tetap)
3. Tulis hasil ke src/lib/products.ts (regenerasi field name/image/affiliateUrl untuk produk yang match).

Tanpa OpenAI/LLM. Tanpa input manual. App ID/Secret dari env, tidak pernah masuk frontend.

Cara pakai:
  SHOPEE_APP_ID=xxx SHOPEE_APP_SECRET=yyy python3 scripts/sync_shopee_products.py
  (tanpa kredensial: resolve + parse ID saja, affiliate tetap dipakai)
"""
import json
import os
import re
import subprocess
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOOGLE_API = "/opt/data/skills/productivity/google-workspace/scripts/google_api.py"
SPREADSHEET_ID = "1JWgph214tsk9HFAeRyG5uhGicxU18RBGQ7O7nVN6CkY"
PRODUCTS_TS = os.path.join(ROOT, "src/lib/products.ts")

# Map nama produk di sheet → id produk di products.ts (match by nama produk sheet)
SHEET_TO_ID = {
    "Keyboard mechanical hot-swap": "keyboard-hotswap",
    "Keyboard mechanical switch brown": "keyboard-brown-switch",
    "Keyboard mechanical entry (under 500rb)": "keyboard-mechanical-entry",
    "Switch tester keyboard": "switch-tester",
    "Keyboard mechanical 60%": "keyboard-60",
    "Keycap puller / cleaning kit": "keycap-puller",
    "SSD laptop": "ssd-laptop",
    "RAM laptop": "ram-laptop",
    "USB WiFi adapter": "wifi-adapter",
    "Cooling pad laptop": "cooling-pad",
    "Baterai laptop": "laptop-battery",
    "Charger laptop": "laptop-charger",
    "Penghilang bau kulkas": "fridge-deodorizer",
    "Kotak penyimpanan": "storage-box",
    "Lap microfiber": "microfiber-cloth",
    "Wadah penyimpanan sayuran": "food-storage-container",
    "Kantong ziplock": "ziplock-bag",
    "Wadah kedap udara": "airtight-container",
}


def read_sheet():
    """Baca sheet Produk Affiliate via google_api.py — output JSON array."""
    rng = "Produk Affiliate!A1:G19"
    out = subprocess.run(
        [sys.executable, GOOGLE_API, "sheets", "get", SPREADSHEET_ID, rng],
        capture_output=True, text=True, timeout=60,
    )
    if out.returncode != 0:
        raise RuntimeError(f"google_api.py gagal: {out.stderr[:300]}")
    data = json.loads(out.stdout)
    return data


def resolve_short_link(url: str) -> str:
    if "s.shopee.co.id" not in url:
        return url
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.geturl()


def parse_ids(product_url: str):
    m = re.search(r"/[^/]+/(\d+)/(\d+)", product_url)
    if not m:
        return None, None
    return m.group(1), m.group(2)


def fetch_product(item_id, shop_id, app_id, app_secret):
    """Panggil Shopee Affiliate Open API — foto + judul asli."""
    import base64
    import hashlib
    import hmac
    import time

    path = "/api/v2/affiliate/product/get_product_info"
    query = f"item_id={item_id}&shop_id={shop_id}"
    timestamp = int(time.time())
    basestring = f"{path}|{query}|{timestamp}"
    sig = base64.b64encode(
        hmac.new(app_secret.encode(), basestring.encode(), hashlib.sha256).digest()
    ).decode()
    url = f"https://open-api.affiliate.shopee.co.id{path}?{query}"
    req = urllib.request.Request(url, headers={
        "X-Api-Key": app_id,
        "X-Timestamp": str(timestamp),
        "Authorization": sig,
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode())


def download_image(url: str, dest: str) -> bool:
    """Download foto ke lokal. Skip kalau file sudah ada & tidak kosong. Return True jika ada file."""
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return True  # sudah pernah didownload — skip
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = resp.read()
        if len(data) < 100:
            return False
        with open(dest, "wb") as f:
            f.write(data)
        return True
    except Exception:
        return False


def local_image_path(pid: str) -> str:
    """Path lokal foto produk; cek webp/jpg/png yang sudah ada."""
    for ext in ("webp", "jpg", "png", "jpeg"):
        p = os.path.join(ROOT, "public", "assets", "img", f"affiliate-{pid}.{ext}")
        if os.path.exists(p) and os.path.getsize(p) > 0:
            return p
    return os.path.join(ROOT, "public", "assets", "img", f"affiliate-{pid}.webp")


def mark_sheet_downloaded(rows: list, local_ids: set):
    """Tandai kolom G (Foto Lokal) = ✅ untuk produk yang file-nya sudah ada di lokal."""
    values = []
    for row in rows[1:]:
        sheet_name = row[1] if len(row) > 1 else ""
        pid = SHEET_TO_ID.get(sheet_name)
        values.append(["✅" if pid and pid in local_ids else ""])
    import json as _json
    body = _json.dumps(values, ensure_ascii=False)
    subprocess.run(
        [sys.executable, GOOGLE_API, "sheets", "update", SPREADSHEET_ID, "Produk Affiliate!G2:G19", "--values", body],
        capture_output=True, text=True, timeout=60,
    )
    print(f"  sheet G ditandai: {len(local_ids)} produk sudah punya foto lokal")


def update_products_ts(updates: dict):
    """Update field name/image/affiliateUrl di products.ts berdasarkan id → (name, image, url)."""
    with open(PRODUCTS_TS) as f:
        content = f.read()
    for pid, (name, image, url) in updates.items():
        # affiliateUrl
        content = re.sub(
            rf"(id: '{pid}',.*?affiliateUrl: )'[^']*'",
            rf"\g<1>'{url}'" if url else rf"\g<1>null",
            content, count=1, flags=re.S,
        )
        # name
        content = re.sub(
            rf"(id: '{pid}',\s*name: )'[^']*'",
            rf"\g<1>'{name}'", content, count=1, flags=re.S,
        )
        # image (jangan null kalau ada)
        if image:
            content = re.sub(
                rf"(id: '{pid}',.*?image: )null",
                rf"\g<1>'{image}'", content, count=1, flags=re.S,
            )
    with open(PRODUCTS_TS, "w") as f:
        f.write(content)
    print(f"  products.ts diupdate ({len(updates)} produk)")


def main():
    app_id = os.environ.get("SHOPEE_APP_ID", "")
    app_secret = os.environ.get("SHOPEE_APP_SECRET", "")
    print(f"[1] Baca sheet Produk Affiliate...")
    rows = read_sheet()
    print(f"    {len(rows)-1} baris produk (header diabaikan)")

    updates = {}
    local_ids = set()
    for row in rows[1:]:
        if len(row) < 4:
            continue
        sheet_name = row[1] if len(row) > 1 else ""
        url = row[3] if len(row) > 3 else ""
        foto_url = row[4] if len(row) > 4 else ""
        judul = row[5] if len(row) > 5 else ""
        if not url or "shopee" not in url:
            continue
        pid = SHEET_TO_ID.get(sheet_name)
        if not pid:
            print(f"  SKIP (no id map): {sheet_name}")
            continue

        # Judul: prioritas judul asli dari sheet (kolom F) → nama produk sheet
        name = judul.strip() if judul and judul.strip() else sheet_name

        # Foto: download dari URL sheet (kolom E) ke lokal kalau belum ada
        image = None
        if foto_url and foto_url.startswith("http"):
            ext = "webp" if ".webp" in foto_url else "jpg"
            dest = os.path.join(ROOT, "public", "assets", "img", f"affiliate-{pid}.{ext}")
            ok = download_image(foto_url, dest)
            if ok:
                local_ids.add(pid)
                image = f"affiliate-{pid}.{ext}"
                print(f"  [{pid}] foto: {'sudah ada' if os.path.getsize(dest) > 0 else 'download'} → {image}")
            else:
                print(f"  [{pid}] foto GAGAL download — pakai existing")
        else:
            # Fallback: cek apakah file lokal sudah pernah ada
            p = local_image_path(pid)
            if os.path.exists(p) and os.path.getsize(p) > 0:
                local_ids.add(pid)
                image = os.path.basename(p)

        # Affiliate URL selalu update dari sheet
        updates[pid] = (name, image, url)

        try:
            resolved = resolve_short_link(url)
            shop_id, item_id = parse_ids(resolved)
            print(f"  [{pid}] {sheet_name}: shop={shop_id} item={item_id} | judul={'Y' if judul else 'N'} foto={'Y' if foto_url else 'N'}")
        except Exception as e:
            print(f"  (resolve skip: {e})")

    if updates:
        update_products_ts(updates)
    # Tandai kolom G di sheet — produk yang foto lokalnya sudah ada
    mark_sheet_downloaded(rows, local_ids)
    print(f"[2] Selesai. {len(local_ids)} produk dengan foto lokal.")


if __name__ == "__main__":
    main()
