#!/bin/sh
set -eu

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=replication_password="$POSTGRES_REPLICATION_PASSWORD" \
  --set=app_password="$POSTGRES_APP_PASSWORD" <<'SQL'
CREATE ROLE perfume_app LOGIN ENCRYPTED PASSWORD :'app_password';
ALTER DATABASE perfume OWNER TO perfume_app;
GRANT CREATE ON SCHEMA public TO perfume_app;
CREATE ROLE perfume_replica WITH REPLICATION LOGIN ENCRYPTED PASSWORD :'replication_password';
SQL

printf '\nhost replication perfume_replica 0.0.0.0/0 scram-sha-256\n' >> "$PGDATA/pg_hba.conf"
