# Backup & Restart Strategy

## Automatic Restarts

All containers are configured with `restart: unless-stopped` in `docker-compose.yml`.
This means:
- Docker daemon restarts containers on crash or after host reboot.
- Containers are only stopped if explicitly stopped with `docker compose stop`.

### Verify restart policy
```bash
docker inspect taskapp_api | grep -A3 RestartPolicy
```

---

## Database Backups

### Manual backup
```bash
./scripts/backup.sh
# Creates: /opt/taskapp/backups/db_backup_YYYYMMDD_HHMMSS.sql.gz
```

### Scheduled daily backup via cron
```bash
# Run as the deploy user
crontab -e

# Add this line — runs at 2:00 AM daily
0 2 * * * /opt/taskapp/scripts/backup.sh >> /opt/taskapp/backups/backup.log 2>&1
```

### Retention policy
Backups older than **7 days** are automatically deleted by the backup script.

### Offsite backup (recommended)
Sync backups to object storage after each run:
```bash
# Add to backup.sh after the prune step (requires aws CLI + IAM role)
aws s3 sync "$BACKUP_DIR" s3://your-bucket/taskapp/db-backups/ \
  --delete --storage-class STANDARD_IA
```

---

## Restore from backup
```bash
./scripts/restore.sh /opt/taskapp/backups/db_backup_20240601_020000.sql.gz
```

---

## Redis Persistence

Redis is configured with `--appendonly yes` (AOF mode).  
The AOF log is stored in the named volume `redis_data` and survives container restarts.

---

## Deployment Rollback

If a bad image is deployed:

```bash
# On the VPS — roll back to the previous image tag
cd /opt/taskapp
export IMAGE_TAG=sha-abc1234   # previous good tag from GHCR
docker compose pull api
docker compose up -d --no-deps api
```

Find previous image tags at:
`https://github.com/<your-org>/<repo>/pkgs/container/<repo>`

---

## Health Check Summary

| Check | Endpoint | Interval | Retries |
|-------|----------|----------|---------|
| FastAPI container | `GET /health` (internal) | 30s | 3 |
| PostgreSQL | `pg_isready` | 10s | 5 |
| Redis | `redis-cli ping` | 10s | 5 |
| NGINX | `nginx -t` | 30s | 3 |

Docker will automatically restart any container whose health check fails `retries` times.
