#!/usr/bin/env bash
set -euo pipefail

DOMAIN="${DOMAIN:-infoxvisits.tsunxkittens.app}"
EMAIL="${EMAIL:-admin@tsunstudio.pw}"
APP_PORT="${APP_PORT:-8076}"
PROJECT_DIR="${PROJECT_DIR:-$(pwd)}"
IMAGE_NAME="${IMAGE_NAME:-tsun-ff-infoxvisits}"
CONTAINER_NAME="${CONTAINER_NAME:-tsun-ff-infoxvisits}"

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║   TSun FF INFOxVISITS — VPS Setup               ║"
echo "║   Domain : ${DOMAIN}"
echo "║   Port   : ${APP_PORT}"
echo "╚══════════════════════════════════════════════════╝"
echo ""

if [ ! -f "${PROJECT_DIR}/app.py" ] || [ ! -f "${PROJECT_DIR}/Dockerfile" ]; then
  echo "ERROR: PROJECT_DIR must point to the project root (with app.py + Dockerfile)."
  exit 1
fi

echo "=== [1/7] Installing system packages ==="
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx

echo "=== [2/7] Ensuring Docker is installed ==="
if ! command -v docker >/dev/null 2>&1; then
  if apt-cache policy docker-ce 2>/dev/null | grep -q "Candidate:"; then
    sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  else
    sudo apt install -y docker.io
  fi
fi
if ! docker compose version >/dev/null 2>&1; then
  sudo apt install -y docker-compose-plugin 2>/dev/null || true
fi
sudo systemctl enable --now docker nginx

cd "${PROJECT_DIR}"

echo "=== [3/7] Building Docker image ==="
sudo docker build -t "${IMAGE_NAME}:latest" .

echo "=== [4/7] Starting container ==="
sudo docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
if [ -f "${PROJECT_DIR}/docker-compose.yml" ] && docker compose version >/dev/null 2>&1; then
  sudo docker compose up -d --build
else
  sudo docker run -d --name "${CONTAINER_NAME}" --restart always \
    -p "127.0.0.1:${APP_PORT}:${APP_PORT}" -e PYTHONUNBUFFERED=1 "${IMAGE_NAME}:latest"
fi

echo "=== [5/7] Configuring Nginx for ${DOMAIN} ==="
sudo tee "/etc/nginx/sites-available/${DOMAIN}" >/dev/null <<EOF
server {
    listen 80;
    server_name ${DOMAIN};
    client_max_body_size 10m;
    location / {
        proxy_pass http://127.0.0.1:${APP_PORT};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Connection "";
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
        proxy_connect_timeout 10s;
        proxy_buffering off;
    }
}
EOF
sudo ln -sf "/etc/nginx/sites-available/${DOMAIN}" "/etc/nginx/sites-enabled/${DOMAIN}"
sudo rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true
sudo nginx -t
sudo systemctl reload nginx

echo "=== [6/7] Requesting SSL certificate ==="
sudo certbot --nginx -d "${DOMAIN}" --redirect -m "${EMAIL}" --agree-tos -n

echo ""
echo "=== [7/7] Verification ==="
sudo docker ps --filter "name=${CONTAINER_NAME}" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""
echo "✔ Setup complete! https://${DOMAIN}"
