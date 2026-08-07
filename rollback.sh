#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

COMPOSE="docker compose -f docker-compose.prod.yml --env-file .env.prod"
TARGET="${1:-}"

if [ -z "$TARGET" ]; then
  if [ -f .last_deploy_commit ]; then
    TARGET=$(cat .last_deploy_commit)
    echo "==> Rolling back to the previously deployed commit: $TARGET"
  else
    echo "!! No .last_deploy_commit found and no commit given."
    echo "!! Usage: ./rollback.sh <commit-sha>"
    echo "!! Recent commits:"
    git log --oneline -10
    exit 1
  fi
else
  echo "==> Rolling back to requested commit: $TARGET"
fi

CURRENT=$(git rev-parse HEAD)
echo "    current: $(git rev-parse --short "$CURRENT") - $(git log -1 --pretty=%s)"

git fetch origin
git reset --hard "$TARGET"
echo "    now at:  $(git rev-parse --short HEAD) - $(git log -1 --pretty=%s)"

echo "==> Rebuilding backend and web from the rolled-back code"
$COMPOSE build backend web
$COMPOSE up -d

echo "==> Container status"
sleep 5
$COMPOSE ps

echo ""
echo "==> Rollback complete: $(git rev-parse --short HEAD)"
echo ""
echo "NOTE - the database was NOT rolled back. To restore it as well:"
echo "  ls -lht backups/"
echo "  docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T db psql -U marine marine_exam < backups/<file>.sql"
echo "Restoring the database is destructive. Be certain before running it."
echo ""
echo "IMPORTANT - the droplet is now BEHIND origin/main. The next push to main"
echo "will deploy the broken code again. Fix the problem on the laptop and push"
echo "the fix, or revert the bad commit on GitHub, before deploying again."
