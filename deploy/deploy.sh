#!/usr/bin/env bash
# Deploy a git ref (sha or branch) and roll back automatically if /healthz does not come up.
# Usage: ./deploy.sh <sha|branch>        (run from anywhere; operates on /opt/squatchscout)
set -euo pipefail
TARGET="${1:?usage: deploy.sh <sha|branch>}"
APP_DIR=/opt/squatchscout
cd "$APP_DIR"
# Read only what this script needs from the env file rather than sourcing it — .env holds
# values like CRAWLER_USER_AGENT="SquatchScoutBot/0.1 (+{public_url}/about)" that break `source`
# if an operator edits the file and drops the quotes. docker compose loads the rest of
# deploy/.env itself via --project-directory.
API_HOST="$(grep -E '^API_HOST=' deploy/.env | cut -d= -f2- | tr -d '"' | tr -d "'")"
COMPOSE=(docker compose -f deploy/docker-compose.yml --project-directory deploy)
PREV="$(cat deploy/.deployed_sha 2>/dev/null || git rev-parse HEAD)"

deploy_ref() {
  local ref="$1"
  git fetch --quiet origin || return 1
  # Resolve against the just-fetched remote-tracking ref first (so a branch name like "main"
  # picks up what origin now has, not whatever local refs/heads/main pointed at when the box
  # was cloned); fall back to treating the argument as a commit-ish (a sha already works either
  # way since `git fetch` also updates commit objects, not just branch tips).
  local target
  if target="$(git rev-parse --verify --quiet "origin/$ref^{commit}")"; then
    :
  elif target="$(git rev-parse --verify --quiet "$ref^{commit}")"; then
    :
  else
    echo "!! cannot resolve ref '$ref'"; return 1
  fi
  git checkout --quiet --detach "$target" || return 1
  local sha; sha="$(git rev-parse --short HEAD)"
  echo "→ building and starting api @ $sha"
  APP_VERSION="$sha" "${COMPOSE[@]}" up -d --build api caddy postgres || return 1
  echo "→ waiting for https://$API_HOST/healthz to report $sha"
  for i in $(seq 1 30); do
    if curl -fsS --max-time 5 "https://$API_HOST/healthz" 2>/dev/null | grep -q "\"version\": *\"$sha\""; then
      echo "✓ healthy @ $sha"; git rev-parse HEAD > deploy/.deployed_sha; return 0
    fi
    sleep 2
  done
  return 1
}

if deploy_ref "$TARGET"; then
  "${COMPOSE[@]}" image prune -f >/dev/null 2>&1 || true
  exit 0
fi
echo "!! health check failed — rolling back to $PREV"
"${COMPOSE[@]}" logs api --tail 40 || true
deploy_ref "$PREV" && { echo "✓ rolled back to $PREV"; exit 1; }
echo "!! rollback also failed — manual intervention needed"; exit 2
