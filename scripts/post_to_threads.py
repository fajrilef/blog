#!/usr/bin/env python3
"""
Auto-post blog articles to Threads (Meta/Instagram) - using urllib (stdlib)
Usage: python3 post_to_threads.py [--article-slug SLUG] [--category tech|living] [--dry-run]
"""

import os
import sys
import json
import re
import argparse
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from datetime import datetime

# Load .env manually
def load_env():
    env_path = Path("/opt/data/.env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key] = val

load_env()

THREADS_API_BASE = "https://graph.threads.net/v1.0"
INSTAGRAM_GRAPH_BASE = "https://graph.instagram.com/v22.0"

# Config from .env
THREADS_ACCESS_TOKEN = os.getenv("THREADS_ACCESS_TOKEN")
THREADS_USER_ID = os.getenv("THREADS_USER_ID")
BLOG_BASE_URL = "https://lofa.web.id"


def get_latest_article(category: str | None = None) -> dict | None:
    """Get the latest published article from the blog content."""
    content_dir = Path("/opt/data/web-blog-astro/src/content/blog")
    
    articles = []
    for cat in ["tech", "living"]:
        if category and cat != category:
            continue
        cat_path = content_dir / cat
        if not cat_path.exists():
            continue
        for md_file in cat_path.glob("*.mdx"):
            content = md_file.read_text(encoding="utf-8")
            fm_match = re.match(r"---\n(.*?)\n---", content, re.DOTALL)
            if fm_match:
                fm_text = fm_match.group(1)
                fm = {}
                for line in fm_text.split("\n"):
                    if ":" in line:
                        key, val = line.split(":", 1)
                        fm[key.strip()] = val.strip().strip('"')
                
                # Skip drafts
                if fm.get("draft", "").lower() == "true":
                    continue
                
                slug = md_file.stem
                articles.append({
                    "slug": slug,
                    "category": cat,
                    "title": fm.get("title", ""),
                    "description": fm.get("description", ""),
                    "pubDate": fm.get("pubDate", ""),
                    "tags": fm.get("tags", ""),
                    "cover": fm.get("cover", ""),
                })
    
    if not articles:
        return None
    
    # Sort by pubDate descending (newest first)
    articles.sort(key=lambda x: x.get("pubDate", ""), reverse=True)
    return articles[0]


def build_threads_post(article: dict) -> str:
    """Build a Threads post from article data (hook + link)."""
    title = article["title"]
    description = article["description"]
    slug = article["slug"]
    category = article["category"]
    
    # Category emoji
    cat_emoji = "⚙️" if category == "tech" else "🏠"
    cat_label = "Teknologi" if category == "tech" else "Kehidupan"
    
    # Article URL
    article_url = f"{BLOG_BASE_URL}/blog/{category}/{slug}/"
    
    # Build hook (2-3 lines max for Threads)
    hook = f"{cat_emoji} {title}\n\n"
    hook += f"{description[:150]}...\n\n"
    hook += f"📖 Baca selengkapnya: {article_url}\n\n"
    hook += f"#{cat_label} #Lofa #{category}"
    
    # Add relevant hashtags from tags
    if article.get("tags"):
        tags = [t.strip().replace(" ", "") for t in article["tags"].strip("[]").split(",")]
        for tag in tags[:3]:
            hook += f" #{tag}"
    
    return hook


def http_post(url: str, data: dict, files: dict | None = None) -> dict:
    """Simple HTTP POST using urllib."""
    if files:
        # Multipart form data - skip for now, use text-only
        pass
    
    # Text-only post
    encoded_data = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(url, data=encoded_data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"error": e.read().decode("utf-8"), "status": e.code}


def post_to_threads(text: str, image_path: str | None = None) -> dict:
    """Post to Threads via Instagram Graph API."""
    if not THREADS_ACCESS_TOKEN or not THREADS_USER_ID:
        return {
            "success": False,
            "error": "Missing THREADS_ACCESS_TOKEN or THREADS_USER_ID in .env"
        }
    
    # Step 1: Create media container (text-only)
    upload_url = f"{INSTAGRAM_GRAPH_BASE}/{THREADS_USER_ID}/media"
    data = {
        "access_token": THREADS_ACCESS_TOKEN,
        "text": text,
    }
    resp = http_post(upload_url, data)
    
    if "error" in resp:
        return {"success": False, "error": f"Create media failed: {resp['error']}"}
    
    media_id = resp.get("id")
    if not media_id:
        return {"success": False, "error": "No media_id returned"}
    
    # Step 2: Publish the media container
    publish_url = f"{INSTAGRAM_GRAPH_BASE}/{THREADS_USER_ID}/media_publish"
    data = {
        "access_token": THREADS_ACCESS_TOKEN,
        "creation_id": media_id,
    }
    resp = http_post(publish_url, data)
    
    if "error" in resp:
        return {"success": False, "error": f"Publish failed: {resp['error']}"}
    
    return {"success": True, "post_id": resp.get("id")}


def get_article_cover_image(article: dict) -> str | None:
    """Get full path to article cover image."""
    cover = article.get("cover", "")
    if not cover:
        return None
    
    # Check public/assets/img/
    img_path = Path("/opt/data/web-blog-astro/public/assets/img") / cover
    if img_path.exists():
        return str(img_path)
    
    return None


def main():
    parser = argparse.ArgumentParser(description="Auto-post blog article to Threads")
    parser.add_argument("--article-slug", help="Specific article slug to post")
    parser.add_argument("--category", choices=["tech", "living"], help="Filter by category")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be posted without posting")
    args = parser.parse_args()
    
    # Get article
    if args.article_slug:
        content_dir = Path("/opt/data/web-blog-astro/src/content/blog")
        found = None
        for cat in ["tech", "living"]:
            md_file = content_dir / cat / f"{args.article_slug}.mdx"
            if md_file.exists():
                content = md_file.read_text(encoding="utf-8")
                fm_match = re.match(r"---\n(.*?)\n---", content, re.DOTALL)
                if fm_match:
                    fm_text = fm_match.group(1)
                    fm = {}
                    for line in fm_text.split("\n"):
                        if ":" in line:
                            key, val = line.split(":", 1)
                            fm[key.strip()] = val.strip().strip('"')
                    found = {
                        "slug": args.article_slug,
                        "category": cat,
                        "title": fm.get("title", ""),
                        "description": fm.get("description", ""),
                        "pubDate": fm.get("pubDate", ""),
                        "tags": fm.get("tags", ""),
                        "cover": fm.get("cover", ""),
                    }
                break
        article = found
    else:
        article = get_latest_article(args.category)
    
    if not article:
        print("❌ No article found")
        sys.exit(1)
    
    print(f"📝 Article: {article['title']}")
    print(f"📂 Category: {article['category']}")
    print(f"🔗 Slug: {article['slug']}")
    
    # Build post
    post_text = build_threads_post(article)
    print("\n--- POST PREVIEW ---")
    print(post_text)
    print("--- END PREVIEW ---\n")
    
    # Get cover image
    cover_path = get_article_cover_image(article)
    if cover_path:
        print(f"🖼️  Cover image: {cover_path}")
    else:
        print("🖼️  No cover image found")
    
    if args.dry_run:
        print("\n✅ Dry run complete - not posting")
        return
    
    # Post to Threads
    print("\n🚀 Posting to Threads...")
    result = post_to_threads(post_text, cover_path)
    
    if result["success"]:
        print(f"✅ Posted successfully! Post ID: {result['post_id']}")
    else:
        print(f"❌ Failed: {result['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()