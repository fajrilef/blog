#!/usr/bin/env node
// ============================================================
// fetch-shopee-standalone.js — FETCH PRODUK SHOPEE (1 file, tanpa install)
// Jalankan dari LAPTOP/PC yang IP-nya TIDAK diblokir Shopee (bukan server).
//
// Cara pakai (Windows / Mac / Linux):
//   1. Pastikan Node.js terinstall: https://nodejs.org (LTS)
//   2. Simpan file ini + buat file links.txt berisi daftar short link (1 per baris)
//   3. Jalankan:  node fetch-shopee-standalone.js links.txt
//      atau:      node fetch-shopee-standalone.js https://s.shopee.co.id/xxxx
//   4. Hasil: file shopee-products-cache.json di folder yang sama
//   5. Kirim file JSON itu ke Lofa (chat), Lofa pasang ke blog + deploy
//
// Catatan: script ini tidak login, tidak pakai browser automation.
// ============================================================
const fs = require('fs');
const path = require('path');
const https = require('https');

const RATE_LIMIT_MS = Number(process.env.SHOPEE_RATE_LIMIT_MS || 1200);
const TIMEOUT_MS = Number(process.env.SHOPEE_TIMEOUT_MS || 15000);
// Header LENGKAP ala browser asli — penting, karena Shopee cek fingerprint header
const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36';
const BROWSER_HEADERS = {
  'User-Agent': UA,
  'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
  'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
  'Accept-Encoding': 'gzip, deflate, br',
  'Cache-Control': 'no-cache',
  'Pragma': 'no-cache',
  'Sec-Ch-Ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
  'Sec-Ch-Ua-Mobile': '?0',
  'Sec-Ch-Ua-Platform': '"Windows"',
  'Sec-Fetch-Dest': 'document',
  'Sec-Fetch-Mode': 'navigate',
  'Sec-Fetch-Site': 'same-origin',
  'Sec-Fetch-User': '?1',
  'Upgrade-Insecure-Requests': '1',
};

function fetchUrl(url, options = {}) {
  return new Promise((resolve, reject) => {
    const req = https.request(url, { ...options, timeout: TIMEOUT_MS }, (res) => {
      const chunks = [];
      res.on('data', (c) => chunks.push(c));
      res.on('end', () => resolve({ status: res.statusCode, headers: res.headers, body: Buffer.concat(chunks).toString() }));
    });
    req.on('timeout', () => req.destroy(new Error('timeout')));
    req.on('error', reject);
    req.end();
  });
}

function buildHeaders(extra = {}) {
  // Tanpa Accept-Encoding gzip (Node tidak auto-decompress) — sisanya ala browser
  const h = { ...BROWSER_HEADERS };
  delete h['Accept-Encoding'];
  return { ...h, ...extra };
}

async function resolveShortLink(url) {
  const r = await fetchUrl(url, { method: 'HEAD', headers: buildHeaders() });
  return r.headers.location || url;
}

function parseIds(url) {
  const m = url.match(/\/(\d+)\/(\d+)(?:\?|$)/);
  return m ? { shopid: m[1], itemid: m[2] } : null;
}

async function fetchProduct(shortUrl) {
  try {
    const resolved = await resolveShortLink(shortUrl);
    const ids = parseIds(resolved);
    if (!ids) return { shortUrl, error: true, reason: 'tidak bisa parse shopid/itemid' };
    const apiUrl = `https://shopee.co.id/api/v4/item/get?itemid=${ids.itemid}&shopid=${ids.shopid}`;
    const res = await fetchUrl(apiUrl, {
      headers: buildHeaders({ 'Accept': 'application/json', 'Referer': 'https://shopee.co.id/' }),
    });
    if (res.status !== 200) return { shortUrl, shopid: ids.shopid, itemid: ids.itemid, error: true, reason: `API HTTP ${res.status}` };
    let json = null;
    try { json = JSON.parse(res.body); } catch {}
    if (!json || json.error) return { shortUrl, shopid: ids.shopid, itemid: ids.itemid, error: true, reason: `API error ${json?.error ?? 'parse'}` };
    const item = json.item || json.data?.item || json.data || {};
    const hash = item.image || (Array.isArray(item.images) ? item.images[0] : null);
    return {
      shortUrl,
      shopid: ids.shopid,
      itemid: ids.itemid,
      error: false,
      title: item.name || '',
      image: hash ? `https://cf.shopee.co.id/file/${hash}` : null,
    };
  } catch (e) {
    return { shortUrl, error: true, reason: e.message };
  }
}

async function main() {
  const args = process.argv.slice(2);
  if (args.length === 0) {
    console.log('Cara pakai: node fetch-shopee-standalone.js <file.txt>  ATAU  <url1> <url2> ...');
    process.exit(1);
  }
  let links = [];
  for (const a of args) {
    if (fs.existsSync(a)) {
      const lines = fs.readFileSync(a, 'utf8').split(/\r?\n/).map((s) => s.trim()).filter(Boolean);
      links = links.concat(lines);
    } else if (a.includes('shopee')) {
      links.push(a);
    }
  }
  links = [...new Set(links)];
  console.log(`[fetch-shopee] ${links.length} link akan diproses...`);

  const products = {};
  let ok = 0, fail = 0;
  for (const link of links) {
    const r = await fetchProduct(link);
    products[link] = r;
    if (r.error) { fail++; console.log(`  ✗ ${link} → ${r.reason}`); }
    else { ok++; console.log(`  ✓ ${link} → ${(r.title || '').slice(0, 45)}`); }
    await new Promise((r2) => setTimeout(r2, RATE_LIMIT_MS));
  }

  const out = { generatedAt: new Date().toISOString(), products };
  const outFile = path.join(process.cwd(), 'shopee-products-cache.json');
  fs.writeFileSync(outFile, JSON.stringify(out, null, 2));
  console.log(`\n[fetch-shopee] Selesai: ${ok} OK, ${fail} gagal`);
  console.log(`[fetch-shopee] Hasil tersimpan di: ${outFile}`);
  console.log('Kirim file shopee-products-cache.json ke Lofa ya!');
}

main();
