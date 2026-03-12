#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

# Remove stale React SPA build files that intercept Django routes
echo "Cleaning stale static files..."
rm -rf staticfiles/
rm -f static/index.html
rm -f static/manifest.json
rm -f static/asset-manifest.json
rm -rf static/js/main.*.js
rm -rf static/css/main.*.css

python manage.py collectstatic --no-input
python manage.py migrate

