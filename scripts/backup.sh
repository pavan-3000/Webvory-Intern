#!/usr/bin/env bash
# Daily PostgreSQL backup — run via cron:  0 2 * * * /opt/taskapp/scripts/backup.sh

set -euo pipefail

BACKUP_DIR="/opt/taskapp/backups"
RETENTION_DAYS=7
DATE=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/db_backup_$DATE.sql.gz"

# Load env
source /opt/taskapp/.env

mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting backup → $BACKUP_FILE"

docker exec taskapp_db pg_dump \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" \
  | gzip > "$BACKUP_FILE"

echo "[$(date)] Backup complete: $(du -sh "$BACKUP_FILE" | cut -f1)"

# Remove backups older than RETENTION_DAYS
find "$BACKUP_DIR" -name "db_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete
echo "[$(date)] Pruned backups older than $RETENTION_DAYS days"
