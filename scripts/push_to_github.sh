#!/bin/bash
# Finish uploading full Lucy project to GitHub
# Run from the lucy/ project root after cloning or from local full copy.
set -e
cd "$(dirname "$0")/.."
git remote remove origin 2>/dev/null || true
git remote add origin https://github.com/daffadevhosting/lucy.git
git push -u origin main --force
echo "Done → https://github.com/daffadevhosting/lucy"
