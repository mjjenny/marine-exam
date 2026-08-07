#!/usr/bin/env bash
set -euo pipefail

# Engine Room Academy — production deploy script
# Lives at /opt/marine-exam/deploy.sh on marine-exam-prod (root@134.209.153.85)
# Run manually:   ./deploy.sh              (rebuilds + restarts every service)
#                 ./deploy.sh web          (only the web/frontend container)
#                 ./deploy.sh backend      (only the backend container)
# Also run automatically by .github/workflows/deploy.yml on every push to main.

cd "$(dirname "$0")"

COMPOSE="docker compose -f docker-compose.prod.yml --env-file .env.prod"
SERVICES="${*:-}"

echo "==> [1/5] Backing up database"
mkdir -p backups
BACKUP_FILE="backups/backup_$(date +%F_%H%M).sql"
$COMPOSE exec -T db pg_dump -U marine marine_exam > "$BACKUP_FILE"
BACKUP_SIZE=$(stat -c%s "$BACKUP_FILE" 2>/dev/null || stat -f%z "$BACKUP_FILE")
if [ "$BACKUP_SIZE" -lt 100000 ]; then
  echo "!! Backup looks too small ($BACKUP_SIZE bytes) — aborting deploy, nothing changed."
  exit 1
fi
echo "    ok: $BACKUP_FILE ($BACKUP_SIZE bytes)"

echo "==> [2/5] Pulling latest code from origin/main"
git fetch origin
git reset --hard origin/main
echo "    now at $(git rev-parse --short HEAD): $(git log -1 --pretty=%s)"

echo "==> [3/5] Building ${SERVICES:-all services}"
$COMPOSE build $SERVICES

echo "==> [4/5] Restarting ${SERVICES:-all services}"
$COMPOSE up -d $SERVICES

echo "==> [5/5] Health check"
sleep 5
$COMPOSE ps
echo ""
echo "-- last 20 backend log lines --"
$COMPOSE logs --tail=20 backend

echo ""
echo "==> Deploy complete: $(git rev-parse --short HEAD)"
echo "    Old backups accumulate in ./backups — prune anything older than ~7 days periodically."