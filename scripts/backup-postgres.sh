#!/usr/bin/env bash
# Dump the RazorScope PostgreSQL database to a timestamped gzip file.
# Usage: bash scripts/backup-postgres.sh [output-dir]
# Default output dir: ./backups/postgres

set -euo pipefail

OUTPUT_DIR="${1:-$(dirname "$0")/../backups/postgres}"
mkdir -p "$OUTPUT_DIR"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
FILE="$OUTPUT_DIR/razorscope_${TIMESTAMP}.sql.gz"

: "${DATABASE_URL:=postgresql://razorscope:razorscope_dev@localhost:5432/razorscope}"

echo "Backing up to $FILE ..."
pg_dump "$DATABASE_URL" \
  --no-owner \
  --no-acl \
  --format=plain \
  | gzip > "$FILE"

echo "Done: $FILE ($(du -sh "$FILE" | cut -f1))"

# Retain only the 7 most recent backups
ls -t "$OUTPUT_DIR"/*.sql.gz 2>/dev/null | tail -n +8 | xargs -r rm --
echo "Pruned old backups; kept newest 7."
