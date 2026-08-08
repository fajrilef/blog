import { readdir, readFile } from 'node:fs/promises';
import path from 'node:path';

export async function GET(context) {
  const base = 'https://lofa.web.id';
  // Halaman statis + kategori
  const urls = [
    `${base}/`,
    `${base}/tech/`,
    `${base}/living/`,
    `${base}/about/`,
    `${base}/contact/`,
    `${base}/privacy/`,
    `${base}/disclaimer/`,
  ];
  const contentDir = path.join(process.cwd(), 'src/content/blog');
  for (const cat of ['tech', 'living']) {
    const dir = path.join(contentDir, cat);
    let files = [];
    try { files = await readdir(dir); } catch (e) { continue; }
    for (const f of files.filter((x) => x.endsWith('.mdx') || x.endsWith('.md'))) {
      const raw = await readFile(path.join(dir, f), 'utf-8');
      const m = raw.match(/^---\n([\s\S]*?)\n---/);
      let draft = false;
      if (m) {
        const dm = m[1].match(/^draft:\s*(.*)$/m);
        if (dm && dm[1].trim() === 'true') draft = true;
      }
      if (draft) continue;
      const slug = f.replace(/\.(mdx|md)$/, '');
      urls.push(`${base}/${cat}/${slug}/`);
    }
  }
  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls.map((u) => `  <url><loc>${u}</loc></url>`).join('\n')}
</urlset>`;
  return new Response(xml, { headers: { 'Content-Type': 'application/xml' } });
}
