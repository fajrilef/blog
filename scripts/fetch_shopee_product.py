#!/usr/bin/env python3
"""
Shopee Affiliate Product Fetcher — blog Lofa
Resolve short link affiliate → item_id/shop_id → fetch foto+judul via Shopee Affiliate Open API.

Dipakai saat BUILD (bukan frontend) — App ID/Secret dibaca dari env, TIDAK pernah masuk ke frontend.

Cara pakai:
  export SHOPEE_APP_ID="<App ID dari dashboard Shopee Affiliate>"
  export SHOPEE_APP_SECRET="<App Secret>"
  python3 scripts/fetch_shopee_product.py <url_affiliate_atau_short_link>

Output JSON: { item_id, shop_id, name, image, price, currency, shop_name, affiliate_url }
"""
import hashlib
import hmac
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

API_BASE = "https://open-api.affiliate.shopee.co.id"


def resolve_short_link(url: str) -> str:
    """Resolve s.shopee.co.id/xxxx → URL produk penuh (redirect), tanpa scrape halaman."""
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.geturl()


def parse_ids(product_url: str) -> tuple[str, str]:
    """Parse shop_id & item_id dari URL shopee.co.id/<shop>/<shop_id>/<item_id>."""
    m = re.search(r"/[^/]+/(\d+)/(\d+)", product_url)
    if not m:
        raise ValueError(f"Tidak bisa parse item_id/shop_id dari: {product_url}")
    return m.group(1), m.group(2)


def sign_request(path: str, query: str, timestamp: int, app_secret: str) -> str:
    """Signature: HMAC-SHA256 base64 dari 'path|query|timestamp' pakai App Secret."""
    basestring = f"{path}|{query}|{timestamp}"
    return base64_hmac(basestring, app_secret)


def base64_hmac(data: str, key: str) -> str:
    import base64
    return base64.b64encode(hmac.new(key.encode(), data.encode(), hashlib.sha256).digest()).decode()


def fetch_product(item_id: str, shop_id: str, app_id: str, app_secret: str) -> dict:
    path = "/api/v2/affiliate/product/get_product_info"
    query = f"item_id={item_id}&shop_id={shop_id}"
    timestamp = int(time.time())
    signature = sign_request(path, query, timestamp, app_secret)
    url = f"{API_BASE}{path}?{query}"
    req = urllib.request.Request(url, headers={
        "X-Api-Key": app_id,
        "X-Timestamp": str(timestamp),
        "Authorization": signature,
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode())
    # Struktur respons bervariasi; coba beberapa jalur umum
    item = data.get("data", {}).get("product", data.get("data", {}))
    if not item:
        raise ValueError(f"Respons API tidak berisi produk: {json.dumps(data)[:300]}")
    images = item.get("images") or [item.get("image")] or []
    return {
        "item_id": item_id,
        "shop_id": shop_id,
        "name": item.get("name") or item.get("title") or "",
        "image": images[0] if images else None,
        "price": item.get("price") or item.get("price_min") or None,
        "currency": item.get("currency", "IDR"),
        "shop_name": item.get("shop_name") or item.get("shopname") or "",
        "affiliate_url": f"https://s.shopee.co.id/",
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: fetch_shopee_product.py <affiliate-url>", file=sys.stderr)
        sys.exit(1)
    url = sys.argv[1]
    app_id = os.environ.get("SHOPEE_APP_ID", "")
    app_secret = os.environ.get("SHOPEE_APP_SECRET", "")
    if not app_id or not app_secret:
        print("ERROR: SHOPEE_APP_ID / SHOPEE_APP_SECRET belum diset. Ambil dari dashboard Shopee Affiliate → Open API.", file=sys.stderr)
        sys.exit(2)

    # Step 1: resolve short link → URL produk (tanpa scrape)
    resolved = resolve_short_link(url) if "s.shopee.co.id" in url else url
    print(f"[1] Resolved: {resolved}", file=sys.stderr)
    # Step 2: parse IDs
    shop_id, item_id = parse_ids(resolved)
    print(f"[2] shop_id={shop_id} item_id={item_id}", file=sys.stderr)
    # Step 3: fetch via API
    product = fetch_product(item_id, shop_id, app_id, app_secret)
    print(json.dumps(product, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
