#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ENV_FILE=${1:-"$ROOT_DIR/.env.scale"}

compose() {
  docker compose --env-file "$ENV_FILE" -f "$ROOT_DIR/compose.scale.yaml" "$@"
}

if [ ! -f "$ENV_FILE" ]; then
  echo "Scale demo env file not found: $ENV_FILE" >&2
  exit 1
fi

attempt=0
until curl --insecure --fail --silent https://localhost:8443/healthz/ >/dev/null; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 40 ]; then
    echo "HTTPS health check did not become ready." >&2
    compose logs --no-color
    exit 1
  fi
  sleep 2
done

replica_count=$(compose ps --status running --quiet web | wc -l | tr -d ' ')
if [ "$replica_count" -lt 3 ]; then
  echo "Expected at least three web replicas; found $replica_count." >&2
  compose ps
  exit 1
fi

redirect=$(curl --silent --head --output /dev/null --write-out '%{http_code} %{redirect_url}' http://localhost:8080/en/)
case "$redirect" in
  "308 https://localhost:8443"*) ;;
  *) echo "HTTP did not redirect to HTTPS: $redirect" >&2; exit 1 ;;
esac

request=0
while [ "$request" -lt 30 ]; do
  curl --insecure --fail --silent https://localhost:8443/healthz/ >/dev/null
  request=$((request + 1))
done

replica_status=$(compose exec --no-TTY postgres-replica psql -U perfume_app -d perfume -Atc 'SELECT pg_is_in_recovery()')
if [ "$replica_status" != "t" ]; then
  echo "PostgreSQL standby is not in recovery/read-replica mode." >&2
  exit 1
fi

attempt=0
until catalog_count=$(compose exec --no-TTY postgres-replica psql -U perfume_app -d perfume -Atc 'SELECT COUNT(*) FROM store_product' 2>/dev/null) && [ "$catalog_count" -ge 1 ]; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 30 ]; then
    echo "Demo catalog did not replicate to the standby." >&2
    exit 1
  fi
  sleep 2
done

stats=$(curl --fail --silent 'http://localhost:8404/stats;csv')
healthy_backends=$(printf '%s\n' "$stats" | awk -F, 'NR == 1 { for (i = 1; i <= NF; i++) { gsub(/^# /, "", $i); if ($i == "status") status_col = i } } $1 == "perfume_web" && $2 ~ /^web[1-3]$/ && $(status_col) == "UP" { count++ } END { print count + 0 }')
if [ "$healthy_backends" -lt 3 ]; then
  echo "Expected three healthy HAProxy web backends; found $healthy_backends." >&2
  printf '%s\n' "$stats" | grep '^perfume_web,' >&2 || true
  exit 1
fi

serving_backends=$(printf '%s\n' "$stats" | awk -F, 'NR == 1 { for (i = 1; i <= NF; i++) { gsub(/^# /, "", $i); if ($i == "stot") total_col = i } } $1 == "perfume_web" && $2 ~ /^web[1-3]$/ && $(total_col) + 0 > 0 { count++ } END { print count + 0 }')
if [ "$serving_backends" -lt 3 ]; then
  echo "Repeated requests did not reach all three HAProxy backends." >&2
  printf '%s\n' "$stats" | grep '^perfume_web,' >&2 || true
  exit 1
fi

echo "Scale demo passed: HTTPS, redirect, $replica_count web replicas, $healthy_backends healthy proxy backends, and PostgreSQL catalog replication."
