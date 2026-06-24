# Task Manager API — Production Deployment

A production-ready FastAPI application deployed with Docker Compose, NGINX, PostgreSQL, Redis, and GitHub Actions CI/CD.

## Stack

| Component | Technology |
|-----------|------------|
| API | FastAPI + Uvicorn |
| Database | PostgreSQL 16 |
| Cache | Redis 7 |
| Reverse Proxy | NGINX 1.27 |
| Container Runtime | Docker + Docker Compose v2 |
| CI/CD | GitHub Actions → GHCR → SSH deploy |

---

## Project Structure

```
.
├── app/
│   ├── main.py          # FastAPI routes, startup, health check
│   ├── models.py        # SQLAlchemy ORM models
│   ├── schemas.py       # Pydantic request/response schemas
│   ├── database.py      # Async SQLAlchemy engine & session
│   ├── cache.py         # Redis helpers
│   └── config.py        # Settings loaded from environment
├── nginx/
│   ├── nginx.conf       # Main NGINX config
│   └── conf.d/
│       └── default.conf # HTTP→HTTPS redirect, proxy, rate limit, headers
├── scripts/
│   ├── backup.sh        # PostgreSQL dump + prune
│   └── restore.sh       # Restore from dump
├── .github/
│   └── workflows/
│       └── deploy.yml   # Build image → push GHCR → SSH deploy
├── docs/
│   ├── architecture.md  # Architecture diagram
│   ├── ssl-setup.md     # SSL/TLS options
│   ├── security.md      # Server hardening checklist
│   └── backup-strategy.md
├── Dockerfile           # Multi-stage build (builder + runtime)
├── docker-compose.yml   # Production stack
├── docker-compose.dev.yml  # Dev overrides (hot reload, port exposure)
├── .env.example         # Template for environment variables
└── requirements.txt
```

---

## Local Development

### Prerequisites
- Docker Desktop (or Docker Engine + Compose plugin)
- Git

### Steps

```bash
# 1. Clone the repo
git clone https://github.com/<your-org>/<your-repo>.git
cd <your-repo>

# 2. Create environment file
cp .env.example .env
# Edit .env — set passwords at minimum

# 3. Start the dev stack (hot reload enabled)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# API available at:  http://localhost:8000
# Swagger docs:      http://localhost:8000/api/docs
# NGINX (port 8080): http://localhost:8080
```

---

## Production Deployment (VPS)

### 1. Provision the VPS

Tested on Ubuntu 22.04 LTS. Run as root on a fresh server:

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh
usermod -aG docker deploy    # allow deploy user to run docker

# Install Docker Compose plugin
apt install -y docker-compose-plugin

# Harden the server (see docs/security.md for details)
ufw allow 22/tcp && ufw allow 80/tcp && ufw allow 443/tcp && ufw enable
sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
systemctl restart sshd
```

### 2. Clone repo on VPS

```bash
git clone https://github.com/<your-org>/<your-repo>.git /opt/taskapp
cd /opt/taskapp
cp .env.example .env
```

Edit `/opt/taskapp/.env` — set strong values for:
- `POSTGRES_PASSWORD`
- `REDIS_PASSWORD`
- `APP_SECRET_KEY`

### 3. Set up SSL

#### Option A — With a domain (Let's Encrypt)
```bash
apt install -y certbot
certbot certonly --standalone -d yourdomain.com
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ./nginx/ssl/
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem  ./nginx/ssl/
chmod 600 ./nginx/ssl/privkey.pem
```

#### Option B — Self-signed (no domain)
```bash
mkdir -p ./nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ./nginx/ssl/privkey.pem \
  -out    ./nginx/ssl/fullchain.pem \
  -subj   "/CN=localhost"
```

See [docs/ssl-setup.md](docs/ssl-setup.md) for Cloudflare and other options.

### 4. Start the stack

```bash
cd /opt/taskapp
docker compose up -d

# Verify all containers are healthy
docker compose ps
```

### 5. Verify deployment

```bash
curl https://yourdomain.com/health
# Expected: {"status":"healthy","database":"ok","cache":"ok","version":"1.0.0"}
```

---

## GitHub Actions CI/CD Setup

### Required Secrets (Settings → Secrets → Actions)

| Secret | Description |
|--------|-------------|
| `SSH_HOST` | VPS IP or hostname |
| `SSH_USER` | Deploy user (e.g. `deploy`) |
| `SSH_PRIVATE_KEY` | Private key matching the VPS `~/.ssh/authorized_keys` |
| `SSH_PORT` | SSH port (default 22, optional) |

`GITHUB_TOKEN` is provided automatically by GitHub Actions.

### Pipeline Flow

```
git push origin main
    ↓
Build Docker image (multi-stage, layer cache)
    ↓
Push to GHCR (ghcr.io/<org>/<repo>:sha-xxxxx)
    ↓
SSH into VPS
  → git pull
  → docker compose pull api
  → docker compose up -d --no-deps api
    ↓
Health check loop (10 × 5s retries)
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check (DB + Redis status) |
| `GET` | `/api/docs` | Swagger UI |
| `GET` | `/api/v1/tasks` | List all tasks (Redis cached) |
| `POST` | `/api/v1/tasks` | Create a task |
| `GET` | `/api/v1/tasks/{id}` | Get a task |
| `PUT` | `/api/v1/tasks/{id}` | Update a task |
| `DELETE` | `/api/v1/tasks/{id}` | Delete a task |

---

## Logging Strategy

- **Application**: Python `logging` module writes structured text to stdout/stderr; Docker captures it via the `json-file` driver.
- **NGINX**: Access logs in combined format; error logs at `warn` level. Both written to `/var/log/nginx/` (bind-mounted volume for persistence).
- **Log rotation**: Docker `json-file` driver is configured with `max-size: 20m, max-file: 10` per container to prevent disk exhaustion.
- **Viewing logs**:
  ```bash
  docker compose logs -f api
  docker compose logs --tail=100 nginx
  ```

---

## Backup Strategy

See [docs/backup-strategy.md](docs/backup-strategy.md) for full details.

Quick reference:
```bash
# Manual backup
./scripts/backup.sh

# Scheduled (cron — 2 AM daily)
0 2 * * * /opt/taskapp/scripts/backup.sh >> /opt/taskapp/backups/backup.log 2>&1

# Restore
./scripts/restore.sh backups/db_backup_20240101_020000.sql.gz
```

---

## Useful Commands

```bash
# View running services
docker compose ps

# Tail all logs
docker compose logs -f

# Restart only the API (zero DB downtime)
docker compose up -d --no-deps api

# Run a DB shell
docker exec -it taskapp_db psql -U appuser -d appdb

# Run a Redis shell
docker exec -it taskapp_redis redis-cli -a "$REDIS_PASSWORD"

# Stop everything
docker compose down

# Stop and remove volumes (DESTRUCTIVE — deletes all data)
docker compose down -v
```
