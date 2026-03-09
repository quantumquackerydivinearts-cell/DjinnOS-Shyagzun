#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/quantumquackerydivinearts-cell/DjinnOS-Shyagzun.git"
BRANCH="main"
DOMAIN="atelier-api.quantumquackery.com"
EMAIL=""
APP_USER="djinn"
APP_GROUP="djinn"
APP_ROOT="/opt/djinnos"
ENV_FILE="/etc/djinnos/atelier-api.env"
ENABLE_TLS="1"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-url) REPO_URL="$2"; shift 2 ;;
    --branch) BRANCH="$2"; shift 2 ;;
    --domain) DOMAIN="$2"; shift 2 ;;
    --email) EMAIL="$2"; shift 2 ;;
    --app-user) APP_USER="$2"; APP_GROUP="$2"; shift 2 ;;
    --app-root) APP_ROOT="$2"; shift 2 ;;
    --env-file) ENV_FILE="$2"; shift 2 ;;
    --disable-tls) ENABLE_TLS="0"; shift 1 ;;
    *) echo "Unknown argument: $1"; exit 1 ;;
  esac
done

if [[ "$EUID" -ne 0 ]]; then
  echo "Run as root: sudo bash deploy/setup_server.sh ..."
  exit 1
fi

if [[ -z "$EMAIL" && "$ENABLE_TLS" == "1" ]]; then
  echo "Missing --email for TLS setup"
  exit 1
fi

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  git \
  python3 \
  python3-venv \
  python3-pip \
  nginx \
  certbot \
  python3-certbot-nginx

if ! id -u "$APP_USER" >/dev/null 2>&1; then
  useradd --system --create-home --shell /bin/bash "$APP_USER"
fi

mkdir -p "$APP_ROOT"
chown -R "$APP_USER:$APP_GROUP" "$APP_ROOT"

if [[ ! -d "$APP_ROOT/.git" ]]; then
  sudo -u "$APP_USER" git clone "$REPO_URL" "$APP_ROOT"
else
  sudo -u "$APP_USER" git -C "$APP_ROOT" fetch origin
  sudo -u "$APP_USER" git -C "$APP_ROOT" checkout "$BRANCH"
  sudo -u "$APP_USER" git -C "$APP_ROOT" pull --ff-only origin "$BRANCH"
fi

if [[ ! -d "$APP_ROOT/.venv" ]]; then
  sudo -u "$APP_USER" python3 -m venv "$APP_ROOT/.venv"
fi

sudo -u "$APP_USER" "$APP_ROOT/.venv/bin/pip" install --upgrade pip
sudo -u "$APP_USER" "$APP_ROOT/.venv/bin/pip" install -r "$APP_ROOT/apps/atelier-api/requirements.txt"

mkdir -p "$(dirname "$ENV_FILE")"
if [[ ! -f "$ENV_FILE" ]]; then
  cat > "$ENV_FILE" <<'EOF'
KERNEL_BASE_URL=http://127.0.0.1:8000
KERNEL_INTERNAL_BASE_URL=
DATABASE_URL=postgresql+psycopg://atelier:atelier@127.0.0.1:5432/atelier
ADMIN_GATE_CODE=CHANGE_ME
CORS_ALLOWED_ORIGINS=https://quantumquackery.com,https://www.quantumquackery.com,https://quantumquackery.org,https://www.quantumquackery.org,capacitor://localhost,http://localhost
KERNEL_CONNECT_RETRIES=4
KERNEL_CONNECT_BACKOFF_MS=400
EOF
fi
chown root:"$APP_GROUP" "$ENV_FILE"
chmod 640 "$ENV_FILE"

cat > /etc/systemd/system/atelier-kernel.service <<EOF
[Unit]
Description=DjinnOS Shygazun Kernel Service
After=network.target

[Service]
Type=simple
User=$APP_USER
Group=$APP_GROUP
WorkingDirectory=$APP_ROOT/DjinnOS-Shyagzun
ExecStart=$APP_ROOT/.venv/bin/python -m uvicorn shygazun.kernel_service:app --host 127.0.0.1 --port 8000 --app-dir $APP_ROOT/DjinnOS-Shyagzun
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/atelier-api.service <<EOF
[Unit]
Description=Quantum Quackery Atelier API Service
After=network.target atelier-kernel.service
Requires=atelier-kernel.service

[Service]
Type=simple
User=$APP_USER
Group=$APP_GROUP
EnvironmentFile=$ENV_FILE
WorkingDirectory=$APP_ROOT
ExecStart=$APP_ROOT/.venv/bin/python -m uvicorn atelier_api.main:app --host 127.0.0.1 --port 9000 --app-dir $APP_ROOT/apps/atelier-api
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/nginx/sites-available/atelier-api <<EOF
server {
    listen 80;
    server_name $DOMAIN;

    location / {
        proxy_pass http://127.0.0.1:9000;
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
}
EOF

ln -sf /etc/nginx/sites-available/atelier-api /etc/nginx/sites-enabled/atelier-api
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx

systemctl daemon-reload
systemctl enable atelier-kernel atelier-api
systemctl restart atelier-kernel atelier-api

if [[ "$ENABLE_TLS" == "1" ]]; then
  certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "$EMAIL" --redirect
fi

curl -fsS http://127.0.0.1:8000/events >/dev/null
curl -fsS http://127.0.0.1:9000/health >/dev/null

echo "Setup complete"
echo "Environment file: $ENV_FILE"
echo "Edit it now, then run: systemctl restart atelier-api"
