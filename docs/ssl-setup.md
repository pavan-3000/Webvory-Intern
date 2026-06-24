# SSL / TLS Setup Guide

## Option A — Let's Encrypt with Certbot (Production, with domain)

### 1. Install Certbot on the VPS
```bash
sudo apt update
sudo apt install -y certbot
```

### 2. Stop NGINX temporarily and obtain cert
```bash
docker compose stop nginx
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com
```

### 3. Copy certs to the NGINX volume path
```bash
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ./nginx/ssl/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem  ./nginx/ssl/
sudo chmod 600 ./nginx/ssl/privkey.pem
docker compose start nginx
```

### 4. Auto-renewal via cron
```bash
# /etc/cron.d/certbot-renew
0 3 * * * root certbot renew --quiet --deploy-hook "cd /opt/taskapp && docker compose restart nginx"
```

---

## Option B — Self-Signed Certificate (No domain / Dev/Staging)

Used when no domain is available. Browsers will show a warning but the
connection is still encrypted.

```bash
mkdir -p ./nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ./nginx/ssl/privkey.pem \
  -out    ./nginx/ssl/fullchain.pem \
  -subj   "/C=US/ST=State/L=City/O=OrgName/CN=localhost"
```

---

## Option C — Cloudflare Proxy (No cert management)

1. Point your domain's DNS to the VPS IP in Cloudflare.
2. Enable "Proxied" mode (orange cloud).
3. Cloudflare handles TLS to the visitor.
4. Set NGINX to listen on port 80 only (Cloudflare → VPS over HTTP is fine
   when "Full (strict)" mode is enabled with an origin cert from Cloudflare).

---

## TLS Best Practices Already Configured

- TLSv1.2 and TLSv1.3 only (TLS 1.0/1.1 disabled)
- Strong cipher suite (ECDHE only)
- HSTS header with `preload` directive
- OCSP stapling enabled
- Session cache for performance
