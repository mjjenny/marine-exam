#!/usr/bin/env bash
# One-time HTTPS bootstrap for engineroomacademy.org (Nginx + Certbot / Let's Encrypt).
#
# Run this ONCE, after your DNS A record points at this server. It stages a temporary
# self-signed cert so nginx can start, then obtains the real certificate via the
# HTTP-01 webroot challenge and reloads nginx. Renewals are automatic thereafter,
# handled by the "certbot" service in docker-compose.prod.yml.
#
#   chmod +x init-letsencrypt.sh
#   ./init-letsencrypt.sh
set -e

# ── EDIT THESE ──
domains=(engineroomacademy.org www.engineroomacademy.org)
EMAIL="cl76380@gmail.com"             # real address — Let's Encrypt expiry notices go here
STAGING=0                             # set to 1 first to test without hitting rate limits
# ───────────────

RSA_KEY_SIZE=4096
DATA="./certbot"
COMPOSE="docker compose -f docker-compose.prod.yml --env-file .env.prod"
DOMAIN="${domains[0]}"
LIVE_PATH="/etc/letsencrypt/live/$DOMAIN"
domain_args=""
for domain in "${domains[@]}"; do
  domain_args="$domain_args -d $domain"
done

[ -f docker-compose.prod.yml ] || { echo "Run this from the project root."; exit 1; }
[ -f .env.prod ] || { echo ".env.prod not found."; exit 1; }
command -v docker >/dev/null || { echo "docker not found."; exit 1; }

# 1. Recommended TLS options referenced by nginx.conf.
if [ ! -e "$DATA/conf/options-ssl-nginx.conf" ] || [ ! -e "$DATA/conf/ssl-dhparams.pem" ]; then
  echo "### Downloading recommended TLS parameters ..."
  mkdir -p "$DATA/conf"
  curl -sSf https://raw.githubusercontent.com/certbot/certbot/main/certbot/src/certbot/_internal/plugins/nginx/tls_configs/options-ssl-nginx.conf \
    > "$DATA/conf/options-ssl-nginx.conf"
  curl -sSf https://raw.githubusercontent.com/certbot/certbot/main/certbot/src/certbot/ssl-dhparams.pem \
    > "$DATA/conf/ssl-dhparams.pem"
fi

# 2. Temporary self-signed cert so nginx can load the :443 server block and start.
echo "### Creating a temporary certificate for $DOMAIN ..."
mkdir -p "$DATA/conf/live/$DOMAIN" "$DATA/www"
$COMPOSE run --rm --entrypoint sh certbot -c "\
  openssl req -x509 -nodes -newkey rsa:$RSA_KEY_SIZE -days 1 \
    -keyout '$LIVE_PATH/privkey.pem' -out '$LIVE_PATH/fullchain.pem' -subj '/CN=localhost'"

# 3. Start nginx (now able to serve :80 for the challenge and :443 with the temp cert).
echo "### Starting nginx ..."
$COMPOSE up -d web

# 4. Remove the temporary cert, then request the real one via the webroot challenge.
echo "### Removing temporary certificate ..."
$COMPOSE run --rm --entrypoint sh certbot -c "\
  rm -rf /etc/letsencrypt/live/$DOMAIN /etc/letsencrypt/archive/$DOMAIN /etc/letsencrypt/renewal/$DOMAIN.conf"

echo "### Requesting Let's Encrypt certificate for ${domains[*]} ..."
staging_arg=""; [ "$STAGING" != "0" ] && staging_arg="--staging"
$COMPOSE run --rm --entrypoint certbot certbot \
  certonly --webroot -w /var/www/certbot \
  $staging_arg \
  $domain_args \
  --email "$EMAIL" --rsa-key-size "$RSA_KEY_SIZE" \
  --agree-tos --no-eff-email --force-renewal

# 5. Reload nginx with the real certificate.
echo "### Reloading nginx ..."
$COMPOSE exec web nginx -s reload

echo
echo "### Done. https://$DOMAIN should now be served with a valid Let's Encrypt certificate."
echo "### Next: set APP_BASE_URL + SESSION_COOKIE_SECURE in .env.prod, then '$COMPOSE up -d'."
