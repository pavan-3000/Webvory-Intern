#!/usr/bin/env bash
# Restore from a backup file
# Usage: ./scripts/restore.sh /opt/taskapp/backups/db_backup_20240101_020000.sql.gz

set -euo pipefail

BACKUP_FILE="${1:?Usage: $0 <backup_file.sql.gz>}"

if [ ! -f "$BACKUP_FILE" ]; then
  echo "Backup file not found: $BACKUP_FILE"
  exit 1
fi

source /opt/taskapp/.env

echo "WARNING: This will overwrite the database '$POSTGRES_DB'."
read -r -p "Type 'yes' to confirm: " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
  echo "Aborted."
  exit 1
fi

echo "[$(date)] Restoring from $BACKUP_FILE..."

gunzip -c "$BACKUP_FILE" | docker exec -i taskapp_db psql \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB"

echo "[$(date)] Restore complete."
