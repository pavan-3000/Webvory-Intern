# Server Security Measures

## 1. OS-Level Hardening (VPS)

```bash
# Create a deploy user — never use root in production
adduser deploy
usermod -aG sudo,docker deploy

# Disable root SSH login and password auth
sudo sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl restart sshd

# Enable UFW firewall — allow only SSH, HTTP, HTTPS
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# Automatic security updates
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

## 2. Docker Security

- **Non-root container user**: The FastAPI image runs as `appuser` (see Dockerfile).
- **Read-only NGINX config**: Mounted as `:ro`.
- **No privileged containers**: No `privileged: true` anywhere.
- **Network isolation**: DB and Redis are on the `backend` network only; NGINX cannot reach them directly.
- **No exposed DB/Redis ports**: PostgreSQL (5432) and Redis (6379) are never bound to the host interface in production.

## 3. Secrets Management

- All secrets live in `.env` on the server — never committed to git (`.gitignore` covers it).
- Sensitive CI/CD values (SSH key, DB password) are stored as **GitHub Actions Secrets** and injected at deploy time.
- Rotate `APP_SECRET_KEY` and `POSTGRES_PASSWORD` on each environment independently.

## 4. NGINX Security Headers

Configured in `nginx/nginx.conf`:

| Header | Value |
|--------|-------|
| `X-Frame-Options` | `SAMEORIGIN` |
| `X-XSS-Protection` | `1; mode=block` |
| `X-Content-Type-Options` | `nosniff` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Strict-Transport-Security` | `max-age=63072000; includeSubDomains; preload` |
| `server_tokens` | `off` (hides NGINX version) |

## 5. Rate Limiting

NGINX rate limits all API traffic to 30 requests/minute per IP with a burst of 10.
The `/health` endpoint is excluded (used by load balancers and monitoring tools).

## 6. Application Security

- Input validation via Pydantic schemas (strict types, no raw SQL strings).
- SQLAlchemy ORM prevents SQL injection.
- CORS is set to `*` by default — tighten to specific origins in production:
  ```python
  allow_origins=["https://yourdomain.com"]
  ```

## 7. Monitoring & Alerting (Bonus)

Consider adding:
- **Fail2ban** to block IPs that repeatedly fail SSH auth.
- **Uptime monitoring** (UptimeRobot free tier, or Prometheus + Alertmanager).
- **Log aggregation**: ship container JSON logs to a managed service (Logtail, Papertrail, or self-hosted Loki).
