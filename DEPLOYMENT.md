# Production Deployment Guide

Deploys the full stack — **Postgres + MinIO + Flask/gunicorn backend + Nginx (SPA & reverse proxy)** — to a single Ubuntu VPS with Docker Compose.

**What you'll have at the end:** the app live on your server's IP/domain over HTTP, then optionally HTTPS via Let's Encrypt.

Files this guide uses (already in the repo):

| File | Purpose |
|---|---|
| `backend/Dockerfile`, `backend/docker-entrypoint.sh` | Backend image; runs migrations then gunicorn |
| `frontend/Dockerfile`, `frontend/nginx.conf` | Builds the React app, serves it + proxies `/api` |
| `docker-compose.prod.yml` | Orchestrates all four services |
| `.env.prod.example` | Template for your production secrets |

---

## 1. Provision a fresh Ubuntu VPS

1. Create a droplet/VM: **Ubuntu 24.04 LTS**, 2 GB RAM minimum (4 GB comfortable). Add your SSH key.
2. SSH in as root and create a non-root sudo user:
   ```bash
   ssh root@YOUR_SERVER_IP
   adduser deploy
   usermod -aG sudo deploy
   rsync --archive --chown=deploy:deploy ~/.ssh /home/deploy   # copy your SSH key
   ```
3. Configure the firewall (allow SSH + web):
   ```bash
   ufw allow OpenSSH
   ufw allow 80/tcp
   ufw allow 443/tcp
   ufw --force enable
   ```
4. Reconnect as the new user: `ssh deploy@YOUR_SERVER_IP`

---

## 2. Install Docker & the Compose plugin

```bash
# Docker Engine + Compose v2 plugin (official convenience script)
curl -fsSL https://get.docker.com | sudo sh

# Run docker without sudo (log out/in afterwards for it to take effect)
sudo usermod -aG docker $USER
newgrp docker

# Verify
docker --version
docker compose version
```

---

## 3. Transfer your project to the server

**Option A — Git (recommended):**
```bash
cd ~
git clone <your-repo-url> app
cd app
```

**Option B — rsync from your machine** (run locally, from the project folder):
```bash
rsync -av --progress \
  --exclude '.git' --exclude 'backend/.venv' --exclude 'frontend/node_modules' \
  --exclude 'frontend/dist' --exclude 'pgdata' --exclude 'minio-data' \
  --exclude '.env' --exclude '.env.prod' \
  ./ deploy@YOUR_SERVER_IP:~/app/
```

> Do **not** ship `pgdata/`, `minio-data/`, `.venv`, `node_modules`, or any `.env` file — secrets and data are set up fresh on the server (Docker `.dockerignore` files also exclude these from the images).

---

## 4. Set production environment variables securely

```bash
cd ~/app
cp .env.prod.example .env.prod

# Generate a strong Flask secret and a DB password
openssl rand -hex 32     # -> paste into SECRET_KEY
openssl rand -hex 24     # -> use for POSTGRES_PASSWORD / MinIO keys

nano .env.prod
```

In `.env.prod` set at least:
- `SECRET_KEY` — the `openssl rand -hex 32` value
- `POSTGRES_PASSWORD` — a strong password, **and paste the same value into `DATABASE_URL`**
- `STORAGE_ACCESS_KEY` / `STORAGE_SECRET_KEY` — strong random strings
- `ADMIN_NOTIFY_EMAIL`, `MAIL_FROM` — your addresses (SMTP is optional; if blank, emails are just logged)
- Leave `SESSION_COOKIE_SECURE=false` for now (flip to `true` in step 8, once HTTPS is on)

Lock the file down so only you can read it:
```bash
chmod 600 .env.prod
```

> `.env.prod` is git-ignored by convention — never commit it.

---

## 5. Build and start the stack

`nginx.conf` terminates HTTPS and references a Let's Encrypt certificate that doesn't exist yet, so on the **very first** deploy bring up everything **except `web`**; the `web` (Nginx) and `certbot` services are started by the HTTPS bootstrap in §8.

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build db minio backend
```

This builds the images and starts `db`, `minio`, `backend`. The backend's entrypoint **automatically runs `flask db upgrade`** (creating all tables) before gunicorn starts. (On later deploys, once the certificate exists, a plain `up -d --build` brings the whole stack up.)

Check everything is healthy:
```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f backend   # Ctrl-C to stop tailing
```

Create your admin account:
```bash
docker compose -f docker-compose.prod.yml exec backend \
  flask create-admin --email you@example.com --password 'a-strong-password'
```

(The site itself isn't reachable in a browser until Nginx is up — that happens in §8. After that, visit **https://engineroomacademy.org** and log in as the admin.)

---

## 6. Load your content (import the committable seed)

All exam content lives in a single committable seed — **`backend/seeds/content_seed.json`** (produced by `export_content.py`) — so no source PDFs or database dumps are needed. The backend image already bundles this seed **and** the EK Naval sketch PNGs (`backend/seeds/ek_naval_sketches/`), so the whole restore runs inside the container:

```bash
# 1) Restore every subject, topic, diet, canonical answer and question occurrence.
#    (Creates the 5 subjects if absent; a clean per-subject re-import — safe to re-run.)
docker compose -f docker-compose.prod.yml exec backend python seeds/import_content.py

# 2) Re-upload the EK Naval sketch images to MinIO under the exact keys the DB
#    references, so the sketch thumbnails work.
docker compose -f docker-compose.prod.yml exec backend python seeds/restore_sketches.py
```

You should see it restore all five subjects (EK Motor 145/378, General 174/329, Naval 57/123, Electrical 51/123, Oral 246/246) and upload 16 sketches.

**Keeping the seed current.** Whenever you change content, regenerate the file from the source database and commit it:
```bash
python seeds/export_content.py     # -> backend/seeds/content_seed.json  (read-only)
git add backend/seeds/content_seed.json && git commit -m "Refresh content seed"
```

*(A fresh, empty deployment without content also works — skip this section and add questions through the admin "Add Diet" tool.)*

---

## 7. Point your domain (needed for HTTPS)

Add a DNS **A record**: `engineroomacademy.org` → `134.209.153.85`. `nginx.conf` already has `server_name engineroomacademy.org`, so no edit is needed. Confirm DNS has propagated before running §8:
```bash
dig +short engineroomacademy.org      # must return 134.209.153.85
```

---

## 8. Enable HTTPS with Certbot (Let's Encrypt) — one command

The compose file defines a **`certbot`** service (auto-renews every 12h) and the **`web`** service reloads Nginx every 6h so renewed certs are picked up. Both share `./certbot/www` (ACME challenge webroot) and `./certbot/conf` (certificates), and `nginx.conf` serves `/.well-known/acme-challenge/`.

Issuing the **first** certificate is chicken-and-egg (Nginx needs a cert to start the `:443` block, Certbot needs Nginx serving `:80` to validate). The bundled **`init-letsencrypt.sh`** handles it: it stages a temporary self-signed cert, starts Nginx, obtains the real cert via the webroot challenge, and reloads.

```bash
# 1) Set your email (and optionally STAGING=1 to rehearse) in the script header:
nano init-letsencrypt.sh        # edit EMAIL=...   (DOMAIN is already engineroomacademy.org)

# 2) Run it once:
chmod +x init-letsencrypt.sh
./init-letsencrypt.sh
```

> **Tip:** set `STAGING=1` in the script for a first dry run (Let's Encrypt's real endpoint rate-limits ~5 failures/hour/domain). When it succeeds, set `STAGING=0` and re-run to get the trusted certificate.

What it runs under the hood is the standard webroot command:
```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod run --rm --entrypoint certbot certbot \
  certonly --webroot -w /var/www/certbot -d engineroomacademy.org \
  --email you@example.com --agree-tos --no-eff-email
```

Then finish the switch to HTTPS:
1. In `.env.prod`, set `APP_BASE_URL=https://engineroomacademy.org` and `SESSION_COOKIE_SECURE=true`.
2. Bring the whole stack up (this also starts the `certbot` auto-renew service and recreates `backend` with the new env):
   ```bash
   docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
   ```

**Auto-renewal is automatic** — the `certbot` service renews in the background and `web` reloads Nginx every 6h. To force a renewal test:
```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod run --rm --entrypoint certbot certbot renew --dry-run
```

---

## 9. Verify & operate

```bash
# Health
curl -f http://YOUR_SERVER_IP/api/../health   # backend health via container:
docker compose -f docker-compose.prod.yml exec backend \
  python -c "import urllib.request;print(urllib.request.urlopen('http://localhost:8000/health').read())"

# Logs
docker compose -f docker-compose.prod.yml logs -f backend web

# Update after pulling new code
git pull
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build

# Backups — dump the database regularly
docker compose -f docker-compose.prod.yml exec -T db \
  pg_dump -U marine -d marine_exam --no-owner > backup-$(date +%F).sql

# Stop / start
docker compose -f docker-compose.prod.yml down          # stop (keeps volumes/data)
docker compose -f docker-compose.prod.yml up -d          # start again
```

### Production checklist
- [ ] `SECRET_KEY` is a fresh 32-byte random value (not the dev default)
- [ ] Strong `POSTGRES_PASSWORD` and MinIO keys; `DATABASE_URL` password matches
- [ ] `.env.prod` is `chmod 600` and never committed
- [ ] `SESSION_COOKIE_SECURE=true` **after** HTTPS is enabled
- [ ] Only ports **80/443** are open to the internet (MinIO/Postgres stay internal)
- [ ] A database backup routine is in place
