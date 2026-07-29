# Full test suite for Windows PowerShell: Pytest + Playwright E2E.
# Prerequisites: `docker compose up -d db`, Python with backend[dev], Node + Playwright browsers.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"

function Write-Step($msg) { Write-Host "`n=== $msg ===" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "OK  $msg" -ForegroundColor Green }
function Write-Fail($msg) { Write-Host "FAIL  $msg" -ForegroundColor Red }

$backendRc = 1
$e2eRc = 1
$flaskProc = $null

try {
  Write-Step "1/3 Backend Pytest"
  Set-Location $Backend
  $env:FLASK_APP = "wsgi.py"
  $env:PGHOST = if ($env:PGHOST) { $env:PGHOST } else { "localhost" }
  $env:PGPORT = if ($env:PGPORT) { $env:PGPORT } else { "5432" }
  $env:PGUSER = if ($env:PGUSER) { $env:PGUSER } else { "marine" }
  $env:PGPASSWORD = if ($env:PGPASSWORD) { $env:PGPASSWORD } else { "marine" }
  $env:TEST_DB_NAME = if ($env:TEST_DB_NAME) { $env:TEST_DB_NAME } else { "marine_exam_test" }

  python -m pip install -q -e ".[dev]" | Out-Null
  python -m pytest -v --tb=short
  $backendRc = $LASTEXITCODE
  if ($backendRc -eq 0) { Write-Ok "Backend tests passed" } else { Write-Fail "Backend tests failed" }

  Write-Step "2/3 Start Flask + seed E2E users"
  if (-not $env:DATABASE_URL) {
    $env:DATABASE_URL = "postgresql+psycopg2://$($env:PGUSER):$($env:PGPASSWORD)@$($env:PGHOST):$($env:PGPORT)/marine_exam"
  }
  try { python -m flask db upgrade 2>$null } catch {}
  python -m flask seed-e2e

  $stdoutLog = Join-Path $env:TEMP "era-flask-stdout.log"
  $stderrLog = Join-Path $env:TEMP "era-flask-stderr.log"
  $flaskProc = Start-Process -FilePath "python" -ArgumentList "-m","flask","run","--host","127.0.0.1","--port","5000" `
    -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog -PassThru -WindowStyle Hidden

  $ready = $false
  for ($i = 0; $i -lt 40; $i++) {
    try {
      $r = Invoke-WebRequest -Uri "http://127.0.0.1:5000/health" -UseBasicParsing -TimeoutSec 2
      if ($r.StatusCode -eq 200) { $ready = $true; break }
    } catch { Start-Sleep -Milliseconds 500 }
  }
  if (-not $ready) { throw "Flask failed to start - see $stdoutLog and $stderrLog" }
  Write-Ok "Flask ready on :5000"

  Write-Step "3/3 Playwright E2E (Desktop Chrome + Mobile Safari)"
  Set-Location $Frontend
  npm install --silent | Out-Null
  npx playwright install chromium webkit | Out-Null
  if (-not $env:PLAYWRIGHT_BASE_URL) { $env:PLAYWRIGHT_BASE_URL = "http://127.0.0.1:5173" }
  npx playwright test
  $e2eRc = $LASTEXITCODE
  if ($e2eRc -eq 0) { Write-Ok "E2E tests passed" } else { Write-Fail "E2E tests failed" }
}
finally {
  if ($flaskProc -and -not $flaskProc.HasExited) {
    Stop-Process -Id $flaskProc.Id -Force -ErrorAction SilentlyContinue
  }
  Set-Location $Root
}

Write-Host "`n=== Summary ===" -ForegroundColor Cyan
if ($backendRc -eq 0) { Write-Host "  Backend (Pytest):   PASS" -ForegroundColor Green } else { Write-Host "  Backend (Pytest):   FAIL" -ForegroundColor Red }
if ($e2eRc -eq 0) { Write-Host "  E2E (Playwright):   PASS" -ForegroundColor Green } else { Write-Host "  E2E (Playwright):   FAIL" -ForegroundColor Red }
Write-Host "  Playwright HTML report: frontend/playwright-report/"
Write-Host ""

if ($backendRc -ne 0 -or $e2eRc -ne 0) { exit 1 }
Write-Host "All suites passed." -ForegroundColor Green
