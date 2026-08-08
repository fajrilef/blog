import { getCollection } from 'astro:content';
const posts = await getCollection('blog');
console.log('collection size:', posts.length);
for (const p of posts) console.log(' -', p.id, '|', p.data.category, '|', p.data.title);
