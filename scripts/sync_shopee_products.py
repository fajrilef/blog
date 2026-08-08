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
    rng = "Produk Affiliate!A1:E19"
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
    for row in rows[1:]:
        if len(row) < 4:
            continue
        sheet_name, keyword, url = row[1], row[2], row[3] if len(row) > 3 else ""
        if not url or "shopee" not in url:
            continue
        pid = SHEET_TO_ID.get(sheet_name)
        if not pid:
            print(f"  SKIP (no id map): {sheet_name}")
            continue
        try:
            resolved = resolve_short_link(url)
            shop_id, item_id = parse_ids(resolved)
            print(f"  [{pid}] {sheet_name}: shop={shop_id} item={item_id}")
            if app_id and app_secret and shop_id and item_id:
                try:
                    data = fetch_product(item_id, shop_id, app_id, app_secret)
                    item = data.get("data", {}).get("product", data.get("data", {}))
                    name = item.get("name") or item.get("title") or sheet_name
                    imgs = item.get("images") or [item.get("image")] or []
                    image = imgs[0] if imgs else None
                    updates[pid] = (name, image, url)
                    print(f"    OK: {name[:50]} | img={'Y' if image else 'N'}")
                except Exception as e:
                    print(f"    API error ({e}) — pakai data existing, affiliate tetap")
                    updates[pid] = (sheet_name, None, url)
            else:
                print(f"    (no API credentials — resolve OK, affiliate dipakai)")
                updates[pid] = (sheet_name, None, url)
        except Exception as e:
            print(f"  ERROR {sheet_name}: {e}")

    if updates:
        update_products_ts(updates)
    print("[2] Selesai.")


if __name__ == "__main__":
    main()
