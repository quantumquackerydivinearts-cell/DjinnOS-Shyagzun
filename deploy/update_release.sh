#!/usr/bin/env bash
set -euo pipefail

BRANCH="main"
APP_USER="djinn"
APP_ROOT="/opt/djinnos"
VENV="$APP_ROOT/.venv"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --branch) BRANCH="$2"; shift 2 ;;
    --app-user) APP_USER="$2"; shift 2 ;;
    --app-root) APP_ROOT="$2"; VENV="$APP_ROOT/.venv"; shift 2 ;;
    *) echo "Unknown argument: $1"; exit 1 ;;
  esac
done

if [[ "$EUID" -ne 0 ]]; then
  echo "Run as root: sudo bash deploy/update_release.sh"
  exit 1
fi

if [[ ! -d "$APP_ROOT/.git" ]]; then
  echo "Repo not found at $APP_ROOT"
  exit 1
fi

sudo -u "$APP_USER" git -C "$APP_ROOT" fetch origin
sudo -u "$APP_USER" git -C "$APP_ROOT" checkout "$BRANCH"
sudo -u "$APP_USER" git -C "$APP_ROOT" pull --ff-only origin "$BRANCH"

sudo -u "$APP_USER" "$VENV/bin/pip" install --upgrade pip
sudo -u "$APP_USER" "$VENV/bin/pip" install -r "$APP_ROOT/apps/atelier-api/requirements.txt"

systemctl restart atelier-kernel atelier-api

curl -fsS http://127.0.0.1:8000/events >/dev/null
curl -fsS http://127.0.0.1:9000/health

echo "Update complete"
