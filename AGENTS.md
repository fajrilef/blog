# AGENTS.md — Web Blog Lofa (Astro + Tailwind)

## Project
Blog statis "Lofa" — teknologi & kehidupan sehari-hari. Live di https://fajrilef.github.io/blog/ (repo fajrilef/blog).

## Tech Stack
- Astro 7 (static output, base `/blog`)
- Tailwind CSS v4 (via `@tailwindcss/vite`, import di `src/styles/global.css` + `@source` directives)
- MDX content collections (`src/content/blog/tech/*.mdx`, `src/content/blog/living/*.mdx`)
- Font: Manrope (Google Fonts)

## Commands
- Dev: `npm run dev`
- Build: `npm run build` → output `dist/`
- Preview: `npm run preview`
- Endpoint RSS/sitemap: `src/pages/rss.xml.ts`, `src/pages/sitemap.xml.ts` — **tanpa frontmatter** (frontmatter `---` di file .ts/.js menyebabkan rolldown PARSE_ERROR; hanya file .astro yang pakai frontmatter)

## Struktur
- `src/layouts/Layout.astro` — navbar glassmorphism, dark mode toggle (class `.dark` di `<html>`, localStorage `lofa-theme`), search overlay (Ctrl K), footer, semua JS inline
- `src/pages/index.astro` — homepage: hero, featured (artikel terbaru), category pills, editorial grid
- `src/pages/[cat]/index.astro` — halaman kategori (tech/living)
- `src/pages/[cat]/[slug].astro` — halaman artikel: prev/next, related, share
- `src/components/PostCard.astro` — card artikel dengan `data-search` attributes
- `src/components/RelatedArticles.astro` — reusable "Baca juga" (pakai `findRelated` di lib/article.ts)
- `src/components/SEO.astro` — meta canonical/OG/Twitter + JSON-LD (WebSite/BlogPosting)
- `src/components/AdSlot.astro` — placeholder iklan (tidak render apa pun)
- `src/layouts/StaticPage.astro` — layout halaman statis (about/contact/privacy/disclaimer)
- `src/lib/article.ts` — helper slugOf/readTimeOf/fmtDate/findRelated (related: kategori → tag → terbaru)
- `src/lib/author.ts` — default author object (Lofa) + authorLd()
- `src/lib/products.ts` — katalog produk affiliate (affiliateUrl dari Google Sheets "Produk Affiliate" via `scripts/sync_shopee_products.py`)
- `scripts/sync_shopee_products.py` — sync otomatis: baca sheet → resolve s.shopee.co.id → parse shop_id/item_id → fetch foto+judul via Shopee Affiliate Open API (butuh SHOPEE_APP_ID/SECRET env; tanpa itu resolve+affiliate tetap jalan)
- `scripts/fetch_shopee_product.py` — fetch 1 produk (debug/tool)
- `src/content.config.ts` — glob loader `{ pattern: '**/*.{md,mdx}', base: './src/content/blog' }'`

## Konvensi
- Slug artikel = nama file (tanpa ekstensi); di getStaticPaths parse dari `p.id` (`p.id.split('/').slice(1).join('/')`), jangan pakai `p.slug`
- Frontmatter artikel: title, description, pubDate, category (tech|living), tags[], cover (nama file di `public/assets/img/`), draft
- Warna via CSS custom properties di global.css (`--color-canvas`, `--color-ink`, dll) — dark mode pakai varian `-dark`
- Aksen: `text-accent dark:text-accent-dark`; pill aktif = `bg-ink text-canvas`

## Boundaries
- Jangan commit .env / secrets
- Jangan ubah URL artikel existing (breaking SEO) — slug harus stabil
- Jangan hapus `data-search`/`data-title` attributes di card (dipakai search overlay)
- Setiap deploy: `npm run build` → push `dist/` ke branch `main` (Pages serve dari sana) → push source ke branch `source`
- Jangan tambah dependency berat tanpa alasan (proyek ini ringan)
