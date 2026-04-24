#!/usr/bin/env bash
set -euo pipefail

CH_HOST="${CLICKHOUSE_HOST:-localhost}"
CH_PORT="${CLICKHOUSE_HTTP_PORT:-8123}"
CH_USER="${CLICKHOUSE_USER:-razorscope}"
CH_PASS="${CLICKHOUSE_PASSWORD:-razorscope_dev}"
CH_DB="${CLICKHOUSE_DB:-razorscope}"

SCHEMA_DIR="$(cd "$(dirname "$0")/../schema/clickhouse" && pwd)"

echo "Applying ClickHouse schema to ${CH_HOST}:${CH_PORT} db=${CH_DB}"

# Create the database if it doesn't exist
curl -sf "http://${CH_HOST}:${CH_PORT}/" \
  -u "${CH_USER}:${CH_PASS}" \
  --data "CREATE DATABASE IF NOT EXISTS ${CH_DB}" \
  > /dev/null
echo "  Database '${CH_DB}' ready"

# Apply each schema file in order
for f in "${SCHEMA_DIR}"/*.sql; do
  echo "  Applying $(basename "$f")..."
  curl -sf "http://${CH_HOST}:${CH_PORT}/?database=${CH_DB}" \
    -u "${CH_USER}:${CH_PASS}" \
    --data-binary "@${f}"
  echo "  OK"
done

echo "ClickHouse schema applied successfully."
