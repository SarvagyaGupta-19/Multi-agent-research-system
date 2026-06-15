#!/bin/bash
# =============================================================================
# Multi-Agent Research System — EC2 Bootstrap Script
# Run as: sudo bash setup.sh
#
# Tested on: Ubuntu 22.04 LTS (t2.micro)
# =============================================================================

set -euo pipefail

APP_USER="ubuntu"
APP_DIR="/home/${APP_USER}/multi-agent-research"
REPO_URL="https://github.com/SarvagyaGupta-19/Multi-agent-research-system.git"
PYTHON_VERSION="3.12"

echo "=========================================="
echo " Multi-Agent Research System — EC2 Setup"
echo "=========================================="

# --- 1. System packages ---
echo "[1/7] Installing system packages..."
apt-get update -y
apt-get install -y \
    software-properties-common \
    nginx \
    git \
    curl \
    build-essential

# --- 2. Python 3.12 ---
echo "[2/7] Installing Python ${PYTHON_VERSION}..."
add-apt-repository -y ppa:deadsnakes/ppa
apt-get update -y
apt-get install -y \
    python${PYTHON_VERSION} \
    python${PYTHON_VERSION}-venv \
    python${PYTHON_VERSION}-dev

# --- 3. Clone or update repo ---
echo "[3/7] Setting up application..."
if [ -d "${APP_DIR}" ]; then
    echo "  Directory exists, pulling latest..."
    cd "${APP_DIR}"
    sudo -u ${APP_USER} git pull origin main
else
    echo "  Cloning repository..."
    sudo -u ${APP_USER} git clone "${REPO_URL}" "${APP_DIR}"
    cd "${APP_DIR}"
fi

# --- 4. Virtual environment & dependencies ---
echo "[4/7] Creating virtual environment and installing dependencies..."
cd "${APP_DIR}"
sudo -u ${APP_USER} python${PYTHON_VERSION} -m venv .venv
sudo -u ${APP_USER} .venv/bin/pip install --upgrade pip
sudo -u ${APP_USER} .venv/bin/pip install -r requirements.txt

# --- 5. Environment file ---
echo "[5/7] Setting up environment..."
if [ ! -f "${APP_DIR}/.env" ]; then
    cp "${APP_DIR}/.env.example" "${APP_DIR}/.env"
    chown ${APP_USER}:${APP_USER} "${APP_DIR}/.env"
    chmod 600 "${APP_DIR}/.env"
    echo ""
    echo "  ╔══════════════════════════════════════════════════════════╗"
    echo "  ║  ACTION REQUIRED: Edit .env with your API keys!         ║"
    echo "  ║  nano ${APP_DIR}/.env                                   ║"
    echo "  ╚══════════════════════════════════════════════════════════╝"
    echo ""
else
    echo "  .env already exists, skipping..."
fi

# --- 6. Systemd service ---
echo "[6/7] Installing systemd service..."
cp "${APP_DIR}/deploy/research-api.service" /etc/systemd/system/research-api.service
systemctl daemon-reload
systemctl enable research-api
systemctl restart research-api

echo "  Service status:"
systemctl status research-api --no-pager || true

# --- 7. Nginx reverse proxy ---
echo "[7/7] Configuring Nginx..."
cp "${APP_DIR}/deploy/nginx.conf" /etc/nginx/sites-available/research-api
ln -sf /etc/nginx/sites-available/research-api /etc/nginx/sites-enabled/research-api
rm -f /etc/nginx/sites-enabled/default

nginx -t
systemctl restart nginx

echo ""
echo "=========================================="
echo " Setup complete!"
echo "=========================================="
echo ""
echo " Backend:  http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo '<YOUR_EC2_IP>')/health"
echo ""
echo " Useful commands:"
echo "   sudo systemctl status research-api    # Check backend status"
echo "   sudo journalctl -u research-api -f    # Stream backend logs"
echo "   sudo systemctl restart research-api   # Restart backend"
echo "   sudo systemctl restart nginx          # Restart proxy"
echo ""
