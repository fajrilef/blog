import { readdir, readFile } from 'node:fs/promises';
import path from 'node:path';

export async function GET(context) {
  const base = 'https://fajrilef.github.io/blog';
  const contentDir = path.join(process.cwd(), 'src/content/blog');
  const posts = [];
  for (const cat of ['tech', 'living']) {
    const dir = path.join(contentDir, cat);
    let files = [];
    try { files = await readdir(dir); } catch (e) { continue; }
    for (const f of files.filter((x) => x.endsWith('.mdx') || x.endsWith('.md'))) {
      const raw = await readFile(path.join(dir, f), 'utf-8');
      const m = raw.match(/^---\n([\s\S]*?)\n---/);
      const fm = {};
      if (m) {
        for (const ln of m[1].split('\n')) {
          const kv = ln.match(/^([a-zA-Z]+):\s*(.*)$/);
          if (kv) fm[kv[1]] = kv[2].replace(/^"(.*)"$/, '$1').replace(/^'(.*)'$/, '$1');
        }
      }
      if (fm.draft === 'true') continue;
      const slug = f.replace(/\.(mdx|md)$/, '');
      posts.push({
        title: fm.title || slug,
        description: fm.description || '',
        pubDate: new Date(fm.pubDate || '2026-08-08'),
        link: `${base}/${cat}/${slug}/`,
      });
    }
  }
  posts.sort((a, b) => b.pubDate - a.pubDate);
  const items = posts.map((p) => `<item>
  <title>${p.title}</title>
  <link>${p.link}</link>
  <description>${p.description}</description>
  <pubDate>${p.pubDate.toUTCString()}</pubDate>
</item>`).join('\n');
  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>Lofa — Teknologi & kehidupan sehari-hari</title>
  <link>${base}/</link>
  <description>Catatan ringkas, panduan praktis, dan rekomendasi yang jujur.</description>
${items}
</channel>
</rss>`;
  return new Response(xml, { headers: { 'Content-Type': 'application/xml' } });
}
