#!/usr/bin/env node
// fetch-shopee-product.js — prebuild fetcher produk Shopee untuk blog Lofa.
//
// Alur:
//   1. Baca daftar short link Shopee dari dua sumber:
//      - src/content/blog/ (frontmatter `affiliateUrl` / short link di MDX)
//      - src/lib/products.ts (field affiliateUrl)
//      - src/data/shopee-links.json (opsional, daftar manual)
//   2. Untuk tiap short link: resolve redirect → parse shopid + itemid
//   3. Panggil endpoint internal Shopee:
//        https://shopee.co.id/api/v4/item/get?itemid={itemid}&shopid={shopid}
//      dengan header User-Agent + Referer.
//   4. Simpan hasil { shortUrl, title, image, shopid, itemid } ke
//      shopee-products-cache.json (di root project).
//
// Error handling: kalau API gagal/diblokir, tulis entri { error: true }
// agar build TIDAK pernah gagal — komponen fallback ke placeholder.
//
// Cara jalan:  npm run fetch:products   (atau otomatis via prebuild)
const fs = require('fs');
const path = require('path');
const http = require('http');
const https = require('https');

const ROOT = path.resolve(__dirname, '..');
const CACHE_FILE = path.join(ROOT, 'shopee-products-cache.json');
const RATE_LIMIT_MS = Number(process.env.SHOPEE_RATE_LIMIT_MS || 1200); // jeda antar request
const TIMEOUT_MS = Number(process.env.SHOPEE_TIMEOUT_MS || 15000);

const UA =
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36';

// ---------- util ----------
function fetchUrl(url, options = {}) {
  return new Promise((resolve, reject) => {
    const mod = url.startsWith('https') ? https : http;
    const req = mod.request(url, { ...options, timeout: TIMEOUT_MS }, (res) => {
      const chunks = [];
      res.on('data', (c) => chunks.push(c));
      res.on('end', () => resolve({ status: res.statusCode, headers: res.headers, body: Buffer.concat(chunks).toString() }));
    });
    req.on('timeout', () => { req.destroy(new Error('timeout')); });
    req.on('error', reject);
    req.end();
  });
}

function resolveShortLink(url) {
  return fetchUrl(url, { method: 'HEAD', headers: { 'User-Agent': UA } }).then((r) => r.headers.location || url);
}

/** Parse shopid & itemid dari URL: shopee.co.id/<shop>/<shopid>/<itemid> */
function parseIds(url) {
  const m = url.match(/\/(\d+)\/(\d+)(?:\?|$)/);
  if (!m) return null;
  return { shopid: m[1], itemid: m[2] };
}

async function fetchProduct(shortUrl) {
  // 1. Resolve short link → URL final
  const resolved = await resolveShortLink(shortUrl);
  const ids = parseIds(resolved);
  if (!ids) {
    return { shortUrl, resolved, error: true, reason: `tidak bisa parse shopid/itemid dari ${resolved}` };
  }
  // 2. Panggil API internal
  const apiUrl = `https://shopee.co.id/api/v4/item/get?itemid=${ids.itemid}&shopid=${ids.shopid}`;
  const res = await fetchUrl(apiUrl, {
    headers: { 'User-Agent': UA, 'Referer': 'https://shopee.co.id/', 'Accept': 'application/json' },
  });
  if (res.status !== 200) {
    return { shortUrl, shopid: ids.shopid, itemid: ids.itemid, error: true, reason: `HTTP ${res.status}` };
  }
  let json;
  try { json = JSON.parse(res.body); } catch { json = null; }
  if (!json || json.error) {
    return { shortUrl, shopid: ids.shopid, itemid: ids.itemid, error: true, reason: `API error ${json?.error ?? 'parse'}` };
  }
  const item = json.item || json.data?.item || json.data || {};
  const imageHash = item.image || (Array.isArray(item.images) ? item.images[0] : null);
  return {
    shortUrl,
    shopid: ids.shopid,
    itemid: ids.itemid,
    error: false,
    title: item.name || '',
    image: imageHash ? `https://cf.shopee.co.id/file/${imageHash}` : null,
  };
}

// ---------- kumpulkan short links ----------
function collectShortLinks() {
  const links = new Set();
  // a. Dari frontmatter MDX: recommendedProducts (id produk) + affiliateUrl (short link)
  const blogDir = path.join(ROOT, 'src/content/blog');
  const walk = (dir) => {
    for (const f of fs.readdirSync(dir)) {
      const p = path.join(dir, f);
      const st = fs.statSync(p);
      if (st.isDirectory()) walk(p);
      else if (f.endsWith('.mdx') || f.endsWith('.md')) {
        const src = fs.readFileSync(p, 'utf8');
        for (const m of src.matchAll(/https:\/\/s\.shopee\.co\.id\/[A-Za-z0-9]+/g)) {
          links.add(m[0]);
        }
      }
    }
  };
  walk(blogDir);
  // b. Dari data affiliate (products.ts juga berisi affiliateUrl)
  const productsFile = path.join(ROOT, 'src/lib/products.ts');
  if (fs.existsSync(productsFile)) {
    const src = fs.readFileSync(productsFile, 'utf8');
    for (const m of src.matchAll(/https:\/\/s\.shopee\.co\.id\/[A-Za-z0-9]+/g)) {
      links.add(m[0]);
    }
  }
  // c. Manual list opsional
  const manualFile = path.join(ROOT, 'src/data/shopee-links.json');
  if (fs.existsSync(manualFile)) {
    const arr = JSON.parse(fs.readFileSync(manualFile, 'utf8'));
    for (const u of arr) if (typeof u === 'string') links.add(u);
  }
  return [...links];
}

// ---------- main ----------
async function main() {
  const links = collectShortLinks();
  console.log(`[fetch-shopee] ${links.length} short link ditemukan.`);
  if (links.length === 0) {
    console.log('[fetch-shopee] Tidak ada link — buat cache kosong, build tetap jalan.');
    fs.writeFileSync(CACHE_FILE, JSON.stringify({ generatedAt: new Date().toISOString(), products: {} }, null, 2));
    return;
  }

  // Load cache lama (kalau ada) — pertahankan entri yang masih valid
  let cache = { generatedAt: '', products: {} };
  if (fs.existsSync(CACHE_FILE)) {
    try { cache = JSON.parse(fs.readFileSync(CACHE_FILE, 'utf8')); } catch { cache = { generatedAt: '', products: {} }; }
  }

  const results = {};
  let ok = 0, fail = 0;
  for (const link of links) {
    try {
      const r = await fetchProduct(link);
      results[link] = r;
      if (r.error) { fail++; console.log(`  ✗ ${link} → ${r.reason}`); }
      else { ok++; console.log(`  ✓ ${link} → ${(r.title || '').slice(0, 45)}`); }
    } catch (e) {
      fail++;
      results[link] = { shortUrl: link, error: true, reason: e.message };
      console.log(`  ✗ ${link} → ${e.message}`);
    }
    await new Promise((r) => setTimeout(r, RATE_LIMIT_MS));
  }

  cache.generatedAt = new Date().toISOString();
  cache.products = results;
  fs.writeFileSync(CACHE_FILE, JSON.stringify(cache, null, 2));
  console.log(`[fetch-shopee] Selesai: ${ok} OK, ${fail} gagal → ${CACHE_FILE}`);
}

main().catch((e) => {
  console.error('[fetch-shopee] FATAL:', e.message);
  // Jangan pernah gagalkan build: tulis cache minimal
  fs.writeFileSync(CACHE_FILE, JSON.stringify({ generatedAt: new Date().toISOString(), products: {}, fatal: e.message }, null, 2));
  process.exit(0);
});
