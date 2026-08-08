import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const blog = defineCollection({
  loader: glob({ pattern: '**/*.{md,mdx}', base: './src/content/blog' }),
  schema: z.object({
    title: z.string(),
    description: z.string(),
    pubDate: z.coerce.date(),
    updatedDate: z.coerce.date().optional(),
    category: z.enum(['tech', 'living']),
    tags: z.array(z.string()).default([]),
    cover: z.string().optional(),
    draft: z.boolean().default(false),
    /** ID produk dari src/lib/products.ts — tampilkan section "Produk yang Mungkin Berguna" (maks 3) */
    recommendedProducts: z.array(z.string()).default([]),
  }),
});

export const collections = { blog };
