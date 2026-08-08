// Reusable default author object — tidak mengarang kredensial palsu.
export const AUTHOR = {
  name: 'Lofa',
  description:
    'Lofa adalah brand editorial yang menulis catatan ringkas, panduan praktis, dan rekomendasi jujur seputar teknologi dan kehidupan sehari-hari.',
  // Avatar belum tersedia — kosongkan, jangan pakai gambar orang lain.
  avatar: null,
  url: '/blog/about/',
};

export function authorLd() {
  return {
    '@type': 'Person',
    name: AUTHOR.name,
    description: AUTHOR.description,
    url: 'https://lofa.web.id' + AUTHOR.url,
  };
}
