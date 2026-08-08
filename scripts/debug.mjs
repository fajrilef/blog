import { getCollection } from 'astro:content';
const posts = await getCollection('blog');
for (const p of posts) {
  console.log(JSON.stringify({ id: p.id, slug: p.slug, cat: p.data.category }));
}
