#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: scripts/deploy_github.sh <github-remote-url>"
  echo "Example: scripts/deploy_github.sh git@github.com:owner/repo.git"
  exit 1
fi

remote_url="$1"

git remote remove origin 2>/dev/null || true
git remote add origin "$remote_url"
git branch -M main
git push -u origin main
