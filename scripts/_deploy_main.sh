#!/bin/bash
set -euo pipefail
cd /tmp/mainroot

TOKEN=$(grep -E '^GITHUB_TOKEN=' /opt/data/.env | sed 's/^GITHUB_TOKEN=//')
git remote remove origin 2>/dev/null || true
git remote add origin "https://x-access-token:${TOKEN}@github.com/fajrilef/blog.git"
git push --force origin main 2>&1 | tail -8
echo "PUSH_DONE"
