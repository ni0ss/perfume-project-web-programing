#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ENV_FILE="$ROOT_DIR/.env.scale"

if [ ! -f "$ENV_FILE" ]; then
  command -v openssl >/dev/null 2>&1 || {
    echo "OpenSSL is required to create local demo secrets." >&2
    exit 1
  }
  cat > "$ENV_FILE" <<EOF
SCALE_DEMO_DJANGO_SECRET_KEY=$(openssl rand -hex 48)
SCALE_DEMO_POSTGRES_PASSWORD=$(openssl rand -hex 24)
SCALE_DEMO_APP_PASSWORD=$(openssl rand -hex 24)
SCALE_DEMO_REPLICATION_PASSWORD=$(openssl rand -hex 24)
EOF
  chmod 600 "$ENV_FILE"
fi

cd "$ROOT_DIR"
docker compose --env-file "$ENV_FILE" -f compose.scale.yaml up --build --detach --scale web=3 proxy
