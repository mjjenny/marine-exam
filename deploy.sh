#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

COMPOSE="docker compose -f docker-compose.prod.yml --env-file .env.prod"
EXPLICIT_SERVICES="${*:-}"
BACKUP_DIR="backups"
RETENTION_DAYS=7
SITE_URL="https://engineroomacademy.org"

echo "==> [1/7] Backing up database"
mkdir -p "$BACKUP_DIR"
BACKUP_FILE="$BACKUP_DIR/backup_$(date +%F_%H%M).sql"
$COMPOSE exec -T db pg_dump -U marine marine_exam > "$BACKUP_FILE"
BACKUP_SIZE=$(stat -c%s "$BACKUP_FILE" 2>/dev/null || echo 0)
if [ "$BACKUP_SIZE" -lt 100000 ]; then
  echo "!! Backup is only $BACKUP_SIZE bytes - pg_dump almost certainly failed."
  echo "!! Aborting deploy. Nothing has been changed."
  rm -f "$BACKUP_FILE"
  exit 1
fi
echo "    ok: $BACKUP_FILE ($BACKUP_SIZE bytes)"

echo "==> [2/7] Pruning backups older than $RETENTION_DAYS days"
find "$BACKUP_DIR" -name 'backup_*.sql' -type f -mtime +$RETENTION_DAYS -print -delete || true
echo "    $(find "$BACKUP_DIR" -name 'backup_*.sql' -type f | wc -l) backup(s) retained"

PREV_COMMIT=$(git rev-parse HEAD)
echo "$PREV_COMMIT" > .last_deploy_commit
echo "==> [3/7] Rollback point recorded: $PREV_COMMIT"

echo "==> [4/7] Pulling latest code from origin/main"
git fetch origin
git reset --hard origin/main
NEW_COMMIT=$(git rev-parse HEAD)
echo "    $(git rev-parse --short "$PREV_COMMIT") -> $(git rev-parse --short "$NEW_COMMIT")"
echo "    $(git log -1 --pretty=%s)"

echo "==> [5/7] Deciding what to rebuild"
if [ -n "$EXPLICIT_SERVICES" ]; then
  SERVICES="$EXPLICIT_SERVICES"
  echo "    explicitly requested: $SERVICES"
else
  CHANGED=$(git diff --name-only "$PREV_COMMIT" "$NEW_COMMIT" 2>/dev/null || echo "")
  SERVICES=""
  if echo "$CHANGED" | grep -qE '^(docker-compose\.prod\.yml|Dockerfile)'; then
    SERVICES="backend web"
  else
    echo "$CHANGED" | grep -q '^backend/'  && SERVICES="$SERVICES backend"
    echo "$CHANGED" | grep -q '^frontend/' && SERVICES="$SERVICES web"
  fi
  SERVICES=$(echo "$SERVICES" | xargs || true)
  if [ -z "$SERVICES" ]; then
    echo "    no backend/ or frontend/ changes - skipping image build"
  else
    echo "    changed areas require rebuilding: $SERVICES"
  fi
fi

if [ -n "$SERVICES" ]; then
  echo "==> [6/7] Building $SERVICES"
  $COMPOSE build $SERVICES
else
  echo "==> [6/7] Nothing to build"
fi

echo "    Starting/refreshing containers"
$COMPOSE up -d $SERVICES

echo "==> [7/7] Health check"
sleep 5
$COMPOSE ps

echo ""
echo "-- last 20 backend log lines --"
$COMPOSE logs --tail=20 backend || true

echo ""
echo -n "-- $SITE_URL responded: "
curl -sS -o /dev/null -w "%{http_code}\n" --max-time 15 "$SITE_URL" || echo "(unreachable from droplet - check in a browser)"

echo ""
echo "==> Deploy complete: $(git rev-parse --short HEAD)"
echo "    To undo this deploy:  ./rollback.sh"
