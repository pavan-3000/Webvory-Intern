# Architecture Diagram

## High-Level Overview

```
Internet
    │
    ▼
┌─────────────────────────────────────────────────────┐
│                   VPS / Cloud Server                │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │           Docker Host (docker compose)        │  │
│  │                                              │  │
│  │  ┌────────────┐   frontend network           │  │
│  │  │   NGINX    │◄──── :80 / :443              │  │
│  │  │  (proxy)   │                              │  │
│  │  └─────┬──────┘                              │  │
│  │        │ proxy_pass :8000   frontend + backend│  │
│  │  ┌─────▼──────┐                              │  │
│  │  │  FastAPI   │   backend network            │  │
│  │  │  (uvicorn) │                              │  │
│  │  └──┬─────┬───┘                              │  │
│  │     │     │                                  │  │
│  │  ┌──▼──┐ ┌▼─────┐                           │  │
│  │  │ PG  │ │Redis │                           │  │
│  │  │ :54 │ │ :63  │                           │  │
│  │  │ 32  │ │ 79   │                           │  │
│  │  └─────┘ └──────┘                           │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘

GitHub Actions CI/CD
    │
    ├── push to main → build Docker image → push to GHCR
    │
    └── SSH into VPS → docker compose pull & up
```

## Network Segmentation

| Network    | Services                     | Exposed externally |
|------------|------------------------------|--------------------|
| `frontend` | NGINX ↔ FastAPI              | NGINX ports 80/443 |
| `backend`  | FastAPI ↔ PostgreSQL ↔ Redis | No                 |

PostgreSQL and Redis are **never** reachable from outside the server.

## Data Flow

1. Client → NGINX (TLS termination, rate limiting, security headers)
2. NGINX → FastAPI API container (HTTP/1.1 on internal network)
3. FastAPI → Redis (cache read; returns early if hit)
4. FastAPI → PostgreSQL (reads/writes when cache misses)
5. FastAPI → Redis (cache write on miss)
6. Response bubbles back through NGINX to client

## Container Responsibilities

| Container        | Image              | Role                                  |
|------------------|--------------------|---------------------------------------|
| `taskapp_nginx`  | nginx:1.27-alpine  | TLS termination, reverse proxy, rate limit |
| `taskapp_api`    | custom (Dockerfile)| Business logic, REST API              |
| `taskapp_db`     | postgres:16-alpine | Persistent relational store           |
| `taskapp_redis`  | redis:7-alpine     | Cache + session store                 |

## CI/CD Flow

```
Developer → git push origin main
                  │
                  ▼
         GitHub Actions
           ┌─────────────────────────────┐
           │ 1. Build Docker image        │
           │ 2. Push to GHCR              │
           │ 3. SSH → VPS                 │
           │ 4. docker compose pull api   │
           │ 5. docker compose up -d api  │
           │ 6. Health check /health      │
           └─────────────────────────────┘
```
