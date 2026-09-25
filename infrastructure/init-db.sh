#!/bin/sh
set -eu
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --set=reader_password="$READER_PASSWORD" <<'SQL'
CREATE ROLE bg_reader LOGIN PASSWORD :'reader_password';
GRANT CONNECT ON DATABASE bg_transparency TO bg_reader;
GRANT USAGE ON SCHEMA public TO bg_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO bg_reader;
ALTER ROLE bg_reader SET default_transaction_read_only = on;
ALTER ROLE bg_reader SET statement_timeout = '5s';
SQL
