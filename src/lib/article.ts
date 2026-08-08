// Helper artikel: slug, related articles, format tanggal, waktu baca.
// Dipakai oleh halaman artikel & komponen RelatedArticles.

export function slugOf(p: { id: string }): string {
  return p.id.split('/').slice(1).join('/').replace(/\.(md|mdx)$/, '');
}

export function readTimeOf(body: string | undefined): number {
  return Math.max(1, Math.round((body || '').split(/\s+/).length / 200));
}

export function fmtDate(d: Date): string {
  return d.toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' });
}

export const CAT_LABELS: Record<string, string> = { tech: 'Teknologi', living: 'Kehidupan' };

/**
 * Hitung artikel terkait: kategori sama → tag cocok → terbaru lintas kategori.
 * Tidak pernah menyertakan artikel saat ini. Maks `limit`.
 */
export function findRelated<T extends { id: string; data: { category: string; tags: string[] } }>(
  all: T[],
  current: T,
  limit = 3
): T[] {
  const tags = current.data.tags || [];
  const sameCat = all.filter(
    (p) => p.data.category === current.data.category && slugOf(p) !== slugOf(current)
  );
  const others = all.filter(
    (p) => p.data.category !== current.data.category && slugOf(p) !== slugOf(current)
  );
  const dedupe = (arr: T[]) =>
    arr.filter((p, i, self) => self.findIndex((x) => slugOf(x) === slugOf(p)) === i);
  return dedupe([
    ...sameCat.filter((p) => tags.some((t) => (p.data.tags || []).includes(t))),
    ...sameCat,
    ...others,
  ]).slice(0, limit);
}
