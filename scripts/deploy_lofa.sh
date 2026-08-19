#!/bin/bash
# Deploy blog ke Cloudflare Pages (project lofa-blog, branch main)
set -e
cd /opt/data/web-blog-astro

export CLOUDFLARE_API_TOKEN="$(grep -ohP '(?<=^CLOUDFLARE_API_TOKEN=).*' /opt/data/.env)"
export CLOUDFLARE_ACCOUNT_ID="$(grep -ohP '(?<=^CLOUDFLARE_ACCOUNT_ID=).*' /opt/data/.env)"

if [ -z "$CLOUDFLARE_API_TOKEN" ] || [ -z "$CLOUDFLARE_ACCOUNT_ID" ]; then
  echo "ERROR: Cloudflare credentials not found in /opt/data/.env"
  exit 1
fi
echo "Credentials loaded (token ${#CLOUDFLARE_API_TOKEN} chars, account ${#CLOUDFLARE_ACCOUNT_ID} chars)"

/opt/data/.npm-global/bin/wrangler pages deploy dist --project-name=lofa-blog --branch=main 2>&1 | tail -15
