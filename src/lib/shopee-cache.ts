// Pembaca cache produk Shopee — dibaca build-time (Astro server/static).
// Cache dibuat oleh scripts/fetch-shopee-product.js (prebuild).
import fs from 'node:fs';
import path from 'node:path';

export interface ShopeeCacheEntry {
  shortUrl: string;
  shopid?: string;
  itemid?: string;
  error?: boolean;
  reason?: string;
  title?: string;
  image?: string | null;
}

export interface ShopeeCache {
  generatedAt: string;
  products: Record<string, ShopeeCacheEntry>;
}

const CACHE_PATH = path.join(process.cwd(), 'shopee-products-cache.json');

let _cache: ShopeeCache | null = null;

/** Load cache (sekali per proses, lazy). Tidak pernah throw — return kosong kalau gagal. */
export function loadShopeeCache(): ShopeeCache {
  if (_cache) return _cache;
  try {
    if (fs.existsSync(CACHE_PATH)) {
      const raw = fs.readFileSync(CACHE_PATH, 'utf8');
      const parsed = JSON.parse(raw);
      _cache = { generatedAt: parsed.generatedAt || '', products: parsed.products || {} };
    } else {
      _cache = { generatedAt: '', products: {} };
    }
  } catch {
    _cache = { generatedAt: '', products: {} };
  }
  return _cache;
}

/**
 * Ambil entri produk dari cache berdasarkan affiliateUrl.
 * - affiliateUrl yang s.shopee.co.id → lookup by exact match.
 * - affiliateUrl yang sudah berupa URL produk → lookup by resolved URL (fallback: match itemid).
 * Return null jika tidak ada (komponen fallback ke placeholder).
 */
export function getCachedProduct(affiliateUrl: string): ShopeeCacheEntry | null {
  const cache = loadShopeeCache();
  if (!affiliateUrl) return null;
  // Exact match
  if (cache.products[affiliateUrl]) return cache.products[affiliateUrl];
  // Match by itemid di URL (misal URL sudah resolve)
  const m = affiliateUrl.match(/(\d+)\/(\d+)(?:\?|$)/);
  if (m) {
    const itemid = m[2];
    for (const entry of Object.values(cache.products)) {
      if (entry.itemid === itemid) return entry;
    }
  }
  return null;
}

/** Judul dari cache atau null. */
export function cachedProductTitle(affiliateUrl: string): string | null {
  const e = getCachedProduct(affiliateUrl);
  return e && !e.error && e.title ? e.title : null;
}

/** Gambar (URL lengkap) dari cache atau null. */
export function cachedProductImage(affiliateUrl: string): string | null {
  const e = getCachedProduct(affiliateUrl);
  return e && !e.error && e.image ? e.image : null;
}
