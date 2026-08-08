#!/usr/bin/env node
// fetch-shopee-cookie.js — TES: API Shopee dengan cookie anonim SPC_F (dari homepage, BUKAN login)
// SPC_F = cookie anti-bot yang Shopee berikan ke SEMUA pengunjung homepage (anonim, bukan session akun)
const https = require('https');

const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36';

function fetch(url, opts = {}) {
  return new Promise((resolve, reject) => {
    const req = https.request(url, opts, (res) => {
      const chunks = [];
      res.on('data', (c) => chunks.push(c));
      res.on('end', () => resolve({ status: res.statusCode, headers: res.headers, body: Buffer.concat(chunks).toString() }));
    });
    req.on('error', reject);
    req.end();
  });
}

async function main() {
  // 1. Buka homepage → ambil Set-Cookie (SPC_F dan lainnya)
  console.log('[1] Buka homepage shopee.co.id...');
  const home = await fetch('https://shopee.co.id/', {
    method: 'GET',
    headers: { 'User-Agent': UA, 'Accept-Language': 'id-ID,id;q=0.9' },
  });
  const setCookies = home.headers['set-cookie'] || [];
  const cookies = setCookies.map((c) => c.split(';')[0]);
  console.log('    Cookies diterima:', cookies.map((c) => c.split('=')[0]).join(', '));
  const cookieStr = cookies.join('; ');

  // 2. Coba API dengan cookie itu
  console.log('[2] Panggil API item/get dengan cookie...');
  const apiUrl = 'https://shopee.co.id/api/v4/item/get?itemid=23311645306&shopid=920928141';
  const res = await fetch(apiUrl, {
    headers: {
      'User-Agent': UA,
      'Referer': 'https://shopee.co.id/',
      'Accept': 'application/json',
      'Cookie': cookieStr,
    },
  });
  console.log('    Status:', res.status);
  const body = res.body.slice(0, 300);
  console.log('    Body:', body);

  // 3. Kalau berhasil, parse item
  try {
    const j = JSON.parse(res.body);
    const item = j.item || j.data?.item || j.data || {};
    if (item.name) {
      console.log('\n🎉 BERHASIL!');
      console.log('   Judul:', item.name);
      console.log('   Image hash:', item.image || (item.images && item.images[0]));
    } else {
      console.log('\n⚠️ API direspons tapi tanpa item — error:', j.error);
    }
  } catch (e) {
    console.log('\n⚠️ Gagal parse JSON');
  }
}

main();
