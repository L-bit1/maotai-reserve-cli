#!/usr/bin/env bash
# 远程部署到 Ubuntu 服务器（通过环境变量传入 SSH，勿把密码写入仓库）
# 用法:
#   export DEPLOY_HOST=139.155.134.97
#   export DEPLOY_USER=ubuntu
#   export DEPLOY_PASS='your-password'
#   export MT_ADMIN_PASSWORD='强密码'
#   export MT_SECRET_KEY='32位以上随机串'
#   ./scripts/deploy-remote.sh

set -euo pipefail

DEPLOY_HOST="${DEPLOY_HOST:?请设置 DEPLOY_HOST}"
DEPLOY_USER="${DEPLOY_USER:-ubuntu}"
DEPLOY_PASS="${DEPLOY_PASS:?请设置 DEPLOY_PASS}"
REMOTE_DIR="/opt/maotai"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if ! command -v sshpass &>/dev/null; then
  echo "请先安装 sshpass: brew install sshpass 或 apt install sshpass"
  exit 1
fi

SSH="sshpass -p ${DEPLOY_PASS} ssh -o StrictHostKeyChecking=no ${DEPLOY_USER}@${DEPLOY_HOST}"
RSYNC="sshpass -p ${DEPLOY_PASS} rsync -az --delete -e 'ssh -o StrictHostKeyChecking=no'"

ADMIN_PASS="${MT_ADMIN_PASSWORD:-Maotai@Admin2026}"
SECRET_KEY="${MT_SECRET_KEY:-$(openssl rand -base64 32)}"

echo "==> 同步代码到 ${DEPLOY_HOST}:${REMOTE_DIR}"
$SSH "sudo mkdir -p ${REMOTE_DIR} && sudo chown -R ${DEPLOY_USER}:${DEPLOY_USER} ${REMOTE_DIR}"
eval $RSYNC \
  --exclude '.venv' --exclude 'node_modules' --exclude '.git' \
  --exclude 'data/credentials.json' --exclude 'config.yaml' \
  --exclude 'reverse/jadx_out' --exclude '备份-*' \
  "${ROOT}/" "${DEPLOY_USER}@${DEPLOY_HOST}:${REMOTE_DIR}/"

echo "==> 服务器安装依赖并构建"
$SSH bash -s <<REMOTE
set -e
export DEBIAN_FRONTEND=noninteractive
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-venv python3-pip nginx rsync curl

cd ${REMOTE_DIR}
python3 -m venv .venv
. .venv/bin/activate
pip install -q -U pip
pip install -q -r requirements.txt -r backend/requirements.txt

if [ ! -f config.yaml ]; then
  cp config.example.yaml config.yaml
  sed -i "s/请改成你自己的随机字符串/${SECRET_KEY}/" config.yaml 2>/dev/null || true
fi
mkdir -p data deploy

cat > deploy/.env <<ENV
MT_ADMIN_USERNAME=admin
MT_ADMIN_PASSWORD=${ADMIN_PASS}
MT_SECRET_KEY=${SECRET_KEY}
MT_CORS_ORIGINS=http://${DEPLOY_HOST}
MT_APP_ROOT=${REMOTE_DIR}
ENV

if command -v npm &>/dev/null; then
  cd web && npm install --silent && npm run build
else
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  sudo apt-get install -y -qq nodejs
  cd web && npm install --silent && npm run build
fi

sudo cp deploy/maotai-api.service /etc/systemd/system/
sudo sed -i "s|User=www-data|User=${DEPLOY_USER}|;s|Group=www-data|Group=${DEPLOY_USER}|" /etc/systemd/system/maotai-api.service
sudo systemctl daemon-reload
sudo systemctl enable maotai-api
sudo systemctl restart maotai-api

sudo cp deploy/nginx-ip.conf /etc/nginx/sites-available/maotai
sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf /etc/nginx/sites-available/maotai /etc/nginx/sites-enabled/maotai
sudo nginx -t && sudo systemctl reload nginx

sudo ufw allow 22/tcp 2>/dev/null || true
sudo ufw allow 80/tcp 2>/dev/null || true
REMOTE

echo ""
echo "部署完成"
echo "  Web:  http://${DEPLOY_HOST}/"
echo "  API:  http://${DEPLOY_HOST}/api/v1/ping"
echo "  账号: admin / ${ADMIN_PASS}"
echo "  请尽快修改服务器密码与 MT_ADMIN_PASSWORD"
