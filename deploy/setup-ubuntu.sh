#!/usr/bin/env bash
# One-time server setup for SquatchScout on Ubuntu 24.04. Idempotent. Usage:
#   curl -fsSL https://raw.githubusercontent.com/<owner>/squatchscout/main/deploy/setup-ubuntu.sh | bash -s -- https://github.com/<owner>/squatchscout.git
set -euo pipefail
REPO_URL="${1:?usage: setup-ubuntu.sh <repo-url>}"
APP_DIR=/opt/squatchscout

echo "→ packages"
sudo apt-get update -qq
sudo apt-get install -y -qq ca-certificates curl git gnupg

if ! command -v docker >/dev/null; then
  echo "→ docker engine + compose plugin (official repo)"
  sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
  sudo apt-get update -qq
  sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  sudo usermod -aG docker "$USER"
fi

if ! swapon --show | grep -q swapfile; then
  echo "→ 1 GB swap (image builds on a 1 GB instance can OOM without it)"
  sudo fallocate -l 1G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
fi

if [ ! -d "$APP_DIR/.git" ]; then
  echo "→ clone"
  sudo mkdir -p "$APP_DIR" && sudo chown "$USER":"$USER" "$APP_DIR"
  git clone "$REPO_URL" "$APP_DIR"
fi
cd "$APP_DIR/deploy"
[ -f .env ] || { cp .env.example .env; echo "!! edit $APP_DIR/deploy/.env (POSTGRES_PASSWORD, API_HOST, FRONTEND_ORIGINS, PUBLIC_URL, GROQ_API_KEY) then run: ./deploy.sh main"; }
echo "✓ setup complete. Log out/in once so the docker group applies."
