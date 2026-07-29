#!/usr/bin/env bash
# Full test suite: Pytest (backend) + Playwright E2E (desktop + mobile).
# Prerequisites: Postgres reachable (docker compose up -d db), Python venv with
# backend[dev] installed, Node deps installed in frontend/, Playwright browsers.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

PASS_BACKEND=0
PASS_E2E=0
BACKEND_RC=0
E2E_RC=0

echo -e "${BOLD}${CYAN}═══ Engine Room Academy — full test suite ═══${NC}"
echo

# ── 1. Backend (Pytest) ──────────────────────────────────
echo -e "${BOLD}[1/3] Backend Pytest${NC}"
cd "$BACKEND"

if [[ -d .venv ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate
elif [[ -d ../.venv ]]; then
  # shellcheck disable=SC1091
  source ../.venv/bin/activate 2>/dev/null || source ../.venv/Scripts/activate
fi

export FLASK_APP=wsgi.py
export PGHOST="${PGHOST:-localhost}"
export PGPORT="${PGPORT:-5432}"
export PGUSER="${PGUSER:-marine}"
export PGPASSWORD="${PGPASSWORD:-marine}"
export TEST_DB_NAME="${TEST_DB_NAME:-marine_exam_test}"

python -m pip install -q -e ".[dev]" >/dev/null
set +e
python -m pytest -v --tb=short
BACKEND_RC=$?
set -e
if [[ $BACKEND_RC -eq 0 ]]; then
  PASS_BACKEND=1
  echo -e "${GREEN}✓ Backend tests passed${NC}"
else
  echo -e "${RED}✗ Backend tests failed (exit $BACKEND_RC)${NC}"
fi
echo

# ── 2. Seed E2E users + start Flask ──────────────────────
echo -e "${BOLD}[2/3] Start Flask + seed E2E users${NC}"
# Prefer the main app DB for E2E (not the isolated pytest DB).
export DATABASE_URL="${DATABASE_URL:-postgresql+psycopg2://${PGUSER}:${PGPASSWORD}@${PGHOST}:${PGPORT}/marine_exam}"

# Apply migrations if flask-migrate is available
python -m flask db upgrade 2>/dev/null || true
python -m flask seed-e2e

FLASK_PID=""
cleanup() {
  if [[ -n "${FLASK_PID}" ]] && kill -0 "$FLASK_PID" 2>/dev/null; then
    kill "$FLASK_PID" 2>/dev/null || true
    wait "$FLASK_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

python -m flask run --host 127.0.0.1 --port 5000 >/tmp/era-flask-test.log 2>&1 &
FLASK_PID=$!

# Wait for health
for i in $(seq 1 40); do
  if curl -sf "http://127.0.0.1:5000/health" >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Flask ready on :5000${NC}"
    break
  fi
  if [[ $i -eq 40 ]]; then
    echo -e "${RED}✗ Flask failed to start — see /tmp/era-flask-test.log${NC}"
    exit 1
  fi
  sleep 0.5
done
echo

# ── 3. Playwright E2E ────────────────────────────────────
echo -e "${BOLD}[3/3] Playwright E2E (Desktop Chrome + Mobile Safari)${NC}"
cd "$FRONTEND"
npm install --silent >/dev/null
npx playwright install --with-deps chromium webkit >/dev/null 2>&1 || npx playwright install chromium webkit
export PLAYWRIGHT_BASE_URL="${PLAYWRIGHT_BASE_URL:-http://127.0.0.1:5173}"
set +e
npx playwright test
E2E_RC=$?
set -e
if [[ $E2E_RC -eq 0 ]]; then
  PASS_E2E=1
  echo -e "${GREEN}✓ E2E tests passed${NC}"
else
  echo -e "${RED}✗ E2E tests failed (exit $E2E_RC)${NC}"
fi
echo

# ── Summary ──────────────────────────────────────────────
echo -e "${BOLD}${CYAN}═══ Summary ═══${NC}"
if [[ $PASS_BACKEND -eq 1 ]]; then
  echo -e "  Backend (Pytest):   ${GREEN}PASS${NC}"
else
  echo -e "  Backend (Pytest):   ${RED}FAIL${NC}"
fi
if [[ $PASS_E2E -eq 1 ]]; then
  echo -e "  E2E (Playwright):   ${GREEN}PASS${NC}"
else
  echo -e "  E2E (Playwright):   ${RED}FAIL${NC}"
fi
echo
echo "  Playwright HTML report: frontend/playwright-report/  (npx playwright show-report)"
echo

if [[ $BACKEND_RC -ne 0 || $E2E_RC -ne 0 ]]; then
  exit 1
fi
echo -e "${GREEN}${BOLD}All suites passed.${NC}"
