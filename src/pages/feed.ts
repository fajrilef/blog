export async function GET() {
  return new Response("<rss/>", { headers: { 'Content-Type': 'application/xml' } });
}
