#!/usr/bin/env bash
# Pulls the latest `deploy` branch (built by GitHub Actions — see
# .github/workflows/ci-cd.yml and deploy/ci-cd.md) and brings the live
# PythonAnywhere site up to date. The `deploy` branch already contains the
# compiled frontend baked into backend/frontend_dist/, so this script never
# needs npm/node on the server.
#
# Usage: run manually from a PythonAnywhere Bash console —
#   bash ~/dsl_tracker/deploy.sh
# — or wire it into a Scheduled Task (Tasks tab) for unattended deploys on
# a schedule. See deploy/ci-cd.md for both options and the trade-offs.
set -euo pipefail

# --- Edit these three lines for your account -----------------------------
PROJECT_DIR="$HOME/dsl_tracker"
VENV_DIR="$HOME/.virtualenvs/dsltracker"
WSGI_FILE="/var/www/yourusername_pythonanywhere_com_wsgi.py"
# ---------------------------------------------------------------------------

echo "==> Fetching latest deploy branch..."
cd "$PROJECT_DIR"
git fetch origin deploy
git checkout deploy 2>/dev/null || git checkout -b deploy origin/deploy
git reset --hard origin/deploy

echo "==> Installing any new backend dependencies..."
source "$VENV_DIR/bin/activate"
cd "$PROJECT_DIR/backend"
pip install -r requirements.txt --quiet

echo "==> Applying migrations..."
python manage.py migrate --noinput

echo "==> Collecting static files..."
python manage.py collectstatic --noinput

echo "==> Triggering reload..."
# PythonAnywhere auto-reloads the web app whenever the WSGI file's modified
# time changes — this achieves a reload without needing the PythonAnywhere
# API or an API token at all.
touch "$WSGI_FILE"

echo ""
echo "Deploy complete: $(git rev-parse --short HEAD)"
echo "Live at your PythonAnywhere domain within a few seconds."
