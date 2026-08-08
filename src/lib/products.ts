// Katalog produk untuk section "Produk yang Mungkin Berguna".
// affiliateUrl: null = belum ada link affiliate (jangan tampilkan CTA aktif).
// Diisi saat Fajri kasih URL affiliate dari dashboard Shopee Affiliate.

export interface Product {
  id: string;
  name: string;
  description: string;
  /** Harga dalam Rupiah — null jika tidak diketahui */
  price?: number | null;
  /** Merchant/toko — null jika tidak diketahui */
  merchant?: string | null;
  /** URL affiliate — WAJIB null jika belum ada, jangan pernah mengarang */
  affiliateUrl: string | null;
  /** Nama file gambar di /blog/assets/img/ — null jika belum ada */
  image?: string | null;
}

export const PRODUCTS: Record<string, Product> = {
  // === Keyboard ===
  'keyboard-cleaning-kit': {
    id: 'keyboard-cleaning-kit',
    name: 'Keyboard Cleaning Kit',
    description: 'Set pembersih keyboard lengkap: kuas, blower, dan cairan pembersih untuk membersihkan sela-sela keycap.',
    price: null,
    merchant: null,
    affiliateUrl: null,
    image: null,
  },
  'keycap-puller': {
    id: 'keycap-puller',
    name: 'Keycap Puller (Wire)',
    description: 'Alat pencabut keycap bergaya wire yang aman untuk melepas keycap tanpa merusak switch.',
    price: null,
    merchant: null,
    affiliateUrl: null,
    image: null,
  },
  'cleaning-brush': {
    id: 'cleaning-brush',
    name: 'Brush Pembersih Keyboard',
    description: 'Kuas lembut untuk membersihkan debu dan remah di sela-sela tombol keyboard mechanical.',
    price: null,
    merchant: null,
    affiliateUrl: null,
    image: null,
  },
  'keyboard-hotswap': {
    id: 'keyboard-hotswap',
    name: 'Keyboard Mechanical Hot-Swap',
    description: 'Keyboard mechanical dengan dudukan hot-swap — switch bisa diganti tanpa solder.',
    price: null,
    merchant: null,
    affiliateUrl: null,
    image: null,
  },
  'keyboard-brown-switch': {
    id: 'keyboard-brown-switch',
    name: 'Keyboard Switch Brown (Tactile)',
    description: 'Switch tactile dengan benjolan halus — kompromi nyaman untuk mengetik dan bermain.',
    price: null,
    merchant: null,
    affiliateUrl: null,
    image: null,
  },
  'switch-tester': {
    id: 'switch-tester',
    name: 'Switch Tester Keyboard',
    description: 'Set sampel berbagai switch untuk mencoba rasa merah, cokelat, biru, dan lainnya sebelum membeli.',
    price: null,
    merchant: null,
    affiliateUrl: null,
    image: null,
  },
  'keyboard-mechanical-entry': {
    id: 'keyboard-mechanical-entry',
    name: 'Keyboard Mechanical Entry',
    description: 'Keyboard mechanical ramah kantong untuk pemula yang ingin merasakan perbedaan dari keyboard biasa.',
    price: null,
    merchant: null,
    affiliateUrl: null,
    image: null,
  },
  'keyboard-60': {
    id: 'keyboard-60',
    name: 'Keyboard Mechanical 60%',
    description: 'Keyboard compact 60% — ringkas, hemat tempat meja, tetap nyaman untuk mengetik.',
    price: null,
    merchant: null,
    affiliateUrl: null,
    image: null,
  },

  // === Windows / Gadget ===
  'ssd-laptop': {
    id: 'ssd-laptop',
    name: 'SSD Laptop',
    description: 'Upgrade SSD untuk mempercepat booting dan loading aplikasi secara signifikan.',
    price: null,
    merchant: null,
    affiliateUrl: null,
    image: null,
  },
  'ram-laptop': {
    id: 'ram-laptop',
    name: 'RAM Laptop',
    description: 'Tambah RAM laptop untuk multitasking yang lebih lancar, terutama saat banyak tab terbuka.',
    price: null,
    merchant: null,
    affiliateUrl: null,
    image: null,
  },
  'wifi-adapter': {
    id: 'wifi-adapter',
    name: 'USB WiFi Adapter',
    description: 'Adapter WiFi USB untuk memperbaiki atau memperkuat koneksi nirkabel laptop.',
    price: null,
    merchant: null,
    affiliateUrl: null,
    image: null,
  },
  'cooling-pad': {
    id: 'cooling-pad',
    name: 'Cooling Pad Laptop',
    description: 'Dudukan dengan kipas untuk membantu menurunkan suhu laptop yang cepat panas.',
    price: null,
    merchant: null,
    affiliateUrl: null,
    image: null,
  },
  'laptop-battery': {
    id: 'laptop-battery',
    name: 'Baterai Laptop',
    description: 'Baterai pengganti laptop — pastikan tipe sesuai dengan model laptop kamu.',
    price: null,
    merchant: null,
    affiliateUrl: null,
    image: null,
  },
  'laptop-charger': {
    id: 'laptop-charger',
    name: 'Charger Laptop',
    description: 'Adaptor charger laptop dengan daya dan konektor yang sesuai untuk model laptop kamu.',
    price: null,
    merchant: null,
    affiliateUrl: null,
    image: null,
  },

  // === Rumah ===
  'fridge-deodorizer': {
    id: 'fridge-deodorizer',
    name: 'Penghilang Bau Kulkas',
    description: 'Penyerap bau untuk kulkas — menjaga kulkas tetap segar dan makanan tidak berbau.',
    price: null,
    merchant: null,
    affiliateUrl: null,
    image: null,
  },
  'storage-box': {
    id: 'storage-box',
    name: 'Kotak Penyimpanan',
    description: 'Kotak penyimpanan serbaguna untuk merapikan barang di rumah.',
    price: null,
    merchant: null,
    affiliateUrl: null,
    image: null,
  },
  'microfiber-cloth': {
    id: 'microfiber-cloth',
    name: 'Lap Microfiber',
    description: 'Lap microfiber lembut untuk membersihkan perangkat tanpa meninggalkan goresan.',
    price: null,
    merchant: null,
    affiliateUrl: null,
    image: null,
  },

  // === Dapur / Food Storage ===
  'food-storage-container': {
    id: 'food-storage-container',
    name: 'Wadah Penyimpanan Sayuran',
    description: 'Wadah kedap udara untuk menyimpan sayuran agar tetap segar lebih lama di kulkas.',
    price: null,
    merchant: null,
    affiliateUrl: null,
    image: null,
  },
  'ziplock-bag': {
    id: 'ziplock-bag',
    name: 'Kantong Ziplock',
    description: 'Kantong plastik kedap udara — praktis untuk menyimpan sayur, bumbu, dan bahan makanan.',
    price: null,
    merchant: null,
    affiliateUrl: null,
    image: null,
  },
  'airtight-container': {
    id: 'airtight-container',
    name: 'Wadah Kedap Udara',
    description: 'Wadah kedap udara untuk menyimpan bumbu dan bahan makanan agar awet.',
    price: null,
    merchant: null,
    affiliateUrl: null,
    image: null,
  },
};

/**
 * Ambil produk dari daftar ID, maksimal `limit` (default 3).
 * Produk yang affiliateUrl-nya null tetap ditampilkan TAPI tanpa CTA aktif.
 */
export function getRecommendedProducts(ids: string[] | undefined, limit = 3): Product[] {
  if (!ids || ids.length === 0) return [];
  const found = ids
    .map((id) => PRODUCTS[id])
    .filter((p): p is Product => Boolean(p));
  return found.slice(0, limit);
}

/** True jika ada minimal 1 produk dengan affiliateUrl aktif. */
export function hasActiveAffiliate(products: Product[]): boolean {
  return products.some((p) => Boolean(p.affiliateUrl));
}
