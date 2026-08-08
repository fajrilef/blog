// Katalog produk untuk section "Produk yang Mungkin Berguna".
// affiliateUrl diambil dari Google Sheets "Produk Affiliate" (kolom URL Affiliate) — sync manual.
// Aturan (2026-08-08): SETIAP artikel WAJIB menampilkan 3 produk.
// Prioritas: produk spesifik dari frontmatter → fallback produk kategori (tech/living).

export type ProductCategory = 'tech' | 'living';

export interface Product {
  id: string;
  name: string;
  description: string;
  /** Harga dalam Rupiah — null jika tidak diketahui */
  price?: number | null;
  /** Merchant/toko — null jika tidak diketahui */
  merchant?: string | null;
  /** URL affiliate dari dashboard Shopee Affiliate — null jika belum ada */
  affiliateUrl: string | null;
  /** Nama file gambar di /blog/assets/img/ — null jika belum ada */
  image?: string | null;
  /** Kategori fallback: tech atau living */
  category: ProductCategory;
}

export const PRODUCTS: Record<string, Product> = {
  // === Keyboard (tech) ===
  'keyboard-cleaning-kit': {
    id: 'keyboard-cleaning-kit',
    name: 'Keyboard Cleaning Kit',
    description: 'Set pembersih keyboard lengkap: kuas, blower, dan cairan pembersih untuk membersihkan sela-sela keycap.',
    price: null, merchant: null,
    affiliateUrl: null, image: null, category: 'tech',
  },
  'keycap-puller': {
    id: 'keycap-puller',
    name: 'Keycap Puller (Wire)',
    description: 'Alat pencabut keycap bergaya wire yang aman untuk melepas keycap tanpa merusak switch.',
    price: null, merchant: null,
    affiliateUrl: null, image: null, category: 'tech',
  },
  'cleaning-brush': {
    id: 'cleaning-brush',
    name: 'Brush Pembersih Keyboard',
    description: 'Kuas lembut untuk membersihkan debu dan remah di sela-sela tombol keyboard mechanical.',
    price: null, merchant: null,
    affiliateUrl: null, image: null, category: 'tech',
  },
  'keyboard-hotswap': {
    id: 'keyboard-hotswap',
    name: 'Keyboard Mechanical Hot-Swap',
    description: 'Keyboard mechanical dengan dudukan hot-swap — switch bisa diganti tanpa solder.',
    price: null, merchant: null,
    affiliateUrl: 'https://s.shopee.co.id/2BDuxZTDcv', image: null, category: 'tech',
  },
  'keyboard-brown-switch': {
    id: 'keyboard-brown-switch',
    name: 'Keyboard Switch Brown (Tactile)',
    description: 'Switch tactile dengan benjolan halus — kompromi nyaman untuk mengetik dan bermain.',
    price: null, merchant: null,
    affiliateUrl: 'https://s.shopee.co.id/2VqlMDDBdr', image: null, category: 'tech',
  },
  'switch-tester': {
    id: 'switch-tester',
    name: 'Switch Tester Keyboard',
    description: 'Set sampel berbagai switch untuk mencoba rasa merah, cokelat, biru, dan lainnya sebelum membeli.',
    price: null, merchant: null,
    affiliateUrl: null, image: null, category: 'tech',
  },
  'keyboard-mechanical-entry': {
    id: 'keyboard-mechanical-entry',
    name: 'Keyboard Mechanical Entry',
    description: 'Keyboard mechanical ramah kantong untuk pemula yang ingin merasakan perbedaan dari keyboard biasa.',
    price: null, merchant: null,
    affiliateUrl: 'https://s.shopee.co.id/19QNdm0k6', image: null, category: 'tech',
  },
  'keyboard-60': {
    id: 'keyboard-60',
    name: 'Keyboard Mechanical 60%',
    description: 'Keyboard compact 60% — ringkas, hemat tempat meja, tetap nyaman untuk mengetik.',
    price: null, merchant: null,
    affiliateUrl: null, image: null, category: 'tech',
  },

  // === Windows / Gadget (tech) ===
  'ssd-laptop': {
    id: 'ssd-laptop',
    name: 'SSD Laptop',
    description: 'Upgrade SSD untuk mempercepat booting dan loading aplikasi secara signifikan.',
    price: null, merchant: null,
    affiliateUrl: null, image: null, category: 'tech',
  },
  'ram-laptop': {
    id: 'ram-laptop',
    name: 'RAM Laptop',
    description: 'Tambah RAM laptop untuk multitasking yang lebih lancar, terutama saat banyak tab terbuka.',
    price: null, merchant: null,
    affiliateUrl: 'https://s.shopee.co.id/19QNiAeik', image: null, category: 'tech',
  },
  'wifi-adapter': {
    id: 'wifi-adapter',
    name: 'USB WiFi Adapter',
    description: 'Adapter WiFi USB untuk memperbaiki atau memperkuat koneksi nirkabel laptop.',
    price: null, merchant: null,
    affiliateUrl: null, image: null, category: 'tech',
  },
  'cooling-pad': {
    id: 'cooling-pad',
    name: 'Cooling Pad Laptop',
    description: 'Dudukan dengan kipas untuk membantu menurunkan suhu laptop yang cepat panas.',
    price: null, merchant: null,
    affiliateUrl: null, image: null, category: 'tech',
  },
  'laptop-battery': {
    id: 'laptop-battery',
    name: 'Baterai Laptop',
    description: 'Baterai pengganti laptop — pastikan tipe sesuai dengan model laptop kamu.',
    price: null, merchant: null,
    affiliateUrl: null, image: null, category: 'tech',
  },
  'laptop-charger': {
    id: 'laptop-charger',
    name: 'Charger Laptop',
    description: 'Adaptor charger laptop dengan daya dan konektor yang sesuai untuk model laptop kamu.',
    price: null, merchant: null,
    affiliateUrl: null, image: null, category: 'tech',
  },

  // === Rumah (living) ===
  'fridge-deodorizer': {
    id: 'fridge-deodorizer',
    name: 'Penghilang Bau Kulkas',
    description: 'Penyerap bau untuk kulkas — menjaga kulkas tetap segar dan makanan tidak berbau.',
    price: null, merchant: null,
    affiliateUrl: null, image: null, category: 'living',
  },
  'storage-box': {
    id: 'storage-box',
    name: 'Kotak Penyimpanan',
    description: 'Kotak penyimpanan serbaguna untuk merapikan barang di rumah.',
    price: null, merchant: null,
    affiliateUrl: 'https://s.shopee.co.id/AKZcgjEuYU', image: null, category: 'living',
  },
  'microfiber-cloth': {
    id: 'microfiber-cloth',
    name: 'Lap Microfiber',
    description: 'Lap microfiber lembut untuk membersihkan perangkat tanpa meninggalkan goresan.',
    price: null, merchant: null,
    affiliateUrl: 'https://s.shopee.co.id/9ANfIbaXzX', image: null, category: 'living',
  },

  // === Dapur / Food Storage (living) ===
  'food-storage-container': {
    id: 'food-storage-container',
    name: 'Wadah Penyimpanan Sayuran',
    description: 'Wadah kedap udara untuk menyimpan sayuran agar tetap segar lebih lama di kulkas.',
    price: null, merchant: null,
    affiliateUrl: 'https://s.shopee.co.id/2qTbl2K0FB', image: null, category: 'living',
  },
  'ziplock-bag': {
    id: 'ziplock-bag',
    name: 'Kantong Ziplock',
    description: 'Kantong plastik kedap udara — praktis untuk menyimpan sayur, bumbu, dan bahan makanan.',
    price: null, merchant: null,
    affiliateUrl: 'https://s.shopee.co.id/2gABYicEBR', image: null, category: 'living',
  },
  'airtight-container': {
    id: 'airtight-container',
    name: 'Wadah Kedap Udara',
    description: 'Wadah kedap udara untuk menyimpan bumbu dan bahan makanan agar awet.',
    price: null, merchant: null,
    affiliateUrl: 'https://s.shopee.co.id/60QdWsbitD', image: null, category: 'living',
  },
};

/** Produk default per kategori — dipakai saat artikel tidak punya produk spesifik yang cukup. */
const CATEGORY_DEFAULTS: Record<ProductCategory, string[]> = {
  tech: ['keyboard-hotswap', 'keyboard-brown-switch', 'keyboard-mechanical-entry', 'switch-tester', 'keyboard-60', 'ssd-laptop', 'ram-laptop', 'wifi-adapter'],
  living: ['food-storage-container', 'ziplock-bag', 'airtight-container', 'storage-box', 'microfiber-cloth', 'fridge-deodorizer'],
};

/**
 * Ambil produk untuk artikel — SELALU `limit` (default 3) produk.
 * Prioritas (aturan 2026-08-08: link dari sheet, fallback kategori, jangan pernah kosong):
 * 1. Produk spesifik frontmatter yang PUNYA affiliateUrl aktif
 * 2. Produk KATEGORI (tech/living) yang PUNYA affiliateUrl aktif
 * 3. Produk spesifik frontmatter lainnya (tanpa link — "Segera tersedia")
 * 4. Produk kategori lainnya (tanpa link)
 * 5. Produk kategori lain (terakhir, jangan sampai kosong)
 */
export function getRecommendedProducts(
  ids: string[] | undefined,
  category: ProductCategory,
  limit = 3
): Product[] {
  const used = new Set<string>();
  const result: Product[] = [];
  const push = (p: Product | undefined): boolean => {
    if (!p || used.has(p.id)) return false;
    result.push(p);
    used.add(p.id);
    return true;
  };
  const catProducts = Object.values(PRODUCTS).filter((p) => p.category === category);

  // 1. Produk spesifik ber-affiliate aktif
  for (const id of ids ?? []) {
    const p = PRODUCTS[id];
    if (p?.affiliateUrl && push(p) && result.length >= limit) return result;
  }
  // 2. Produk kategori dengan affiliateUrl aktif
  for (const p of catProducts) {
    if (p.affiliateUrl && push(p) && result.length >= limit) return result;
  }
  // 3. Produk spesifik lainnya (tanpa link)
  for (const id of ids ?? []) {
    if (push(PRODUCTS[id]) && result.length >= limit) return result;
  }
  // 4. Produk kategori lainnya (tanpa link)
  for (const p of catProducts) {
    if (push(p) && result.length >= limit) return result;
  }
  // 5. Produk kategori lain (paling akhir, jangan sampai kosong)
  for (const p of Object.values(PRODUCTS)) {
    if (push(p) && result.length >= limit) return result;
  }
  return result;
}

/** True jika ada minimal 1 produk dengan affiliateUrl aktif. */
export function hasActiveAffiliate(products: Product[]): boolean {
  return products.some((p) => Boolean(p.affiliateUrl));
}
