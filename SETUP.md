# OAMS — Setup Guide

Complete setup for development, production, and office hardware.

> **Building without Docker?** Use **[SETUP_LOCAL.md](SETUP_LOCAL.md)** and `./scripts/setup_local.sh`.

---

## 1. System requirements

### Server (Docker — recommended)

| Item | Minimum | Recommended |
|------|---------|-------------|
| OS | Linux x86_64 (Ubuntu 22.04+) | same |
| CPU | 1 vCPU | 2 vCPU |
| RAM | 1 GB | 2 GB |
| Disk | 10 GB | 20 GB+ |
| Software | Docker 20+, Compose v2 | same |
| Network | Port 8000 (or 443 via reverse proxy) | HTTPS domain |

### Local development (without Docker)

| Item | Requirement |
|------|-------------|
| Python | 3.10+ (3.12 preferred) |
| pip / venv | Required |
| Database | SQLite (default) or Postgres 14+ |
| Browser | Chrome / Edge / Firefox (recent) |

### Office hardware

| Role | Requirement |
|------|-------------|
| Door kiosk | Android tablet (or Chrome device), stand, power, Wi‑Fi |
| Employees | Phone with camera + modern browser |
| TV wallboard | Monitor/TV + Fire Stick / Android box / PC browser |
| Admins | Laptop/desktop browser |

**Note:** Phone camera punch needs **HTTPS** in production (or `localhost` for testing).

---

## 2. Get the code

```bash
cd /path/to/MyProject/oams
```

---

## 3. Development setup (Docker)

### 3.1 Start

```bash
docker compose up --build
```

### 3.2 Verify

```bash
curl http://localhost:8000/api/health
```

Expected:

```json
{"status":"ok","app":"OAMS Office","version":"1.1.0"}
```

Open http://localhost:8000 and sign in:

| Role | Email | Password |
|------|-------|----------|
| Admin | `admin@office.local` | `admin123` |
| Manager | `manager@office.local` | `manager123` |
| Employee | `employee@office.local` | `employee123` |

### 3.3 Stop

```bash
docker compose down
```

---

## 4. Local setup (Python + SQLite)

Use this when Docker is unavailable.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- App: http://localhost:8000  
- DB file: `backend/oams.db` (created automatically)  
- Schema auto-created when `AUTO_CREATE_SCHEMA=true` (default)

Optional env:

```bash
export SECRET_KEY="dev-secret"
export QR_HMAC_SECRET="dev-qr-secret"
export INTERNAL_CRON_SECRET="dev-cron-secret"
```

---

## 5. Production setup (Docker Compose)

### 5.1 Create environment file

```bash
cp .env.example .env
```

Edit `.env` from [`.env.production.example`](.env.production.example) (see also [DEPLOYMENT.md](DEPLOYMENT.md)):

```env
APP_ENV=production
OAMS_DOMAIN=attendance.yourcompany.com
CORS_ORIGINS=https://attendance.yourcompany.com
POSTGRES_PASSWORD=use-a-strong-password
SECRET_KEY=<openssl rand -hex 32>
QR_HMAC_SECRET=<openssl rand -hex 32>
INTERNAL_CRON_SECRET=<openssl rand -hex 32>
RUN_SEED_ON_STARTUP=false
AUTO_CREATE_SCHEMA=false
ENABLE_DOCS=false
```

### 5.2 Start production stack

```bash
docker compose -f docker-compose.prod.yml --env-file .env up --build -d
```

This will:

1. Start Postgres (**not** published to the host)  
2. Run **Alembic migrations** (`migrate` service)  
3. Start the API on the internal network (not published)  
4. Start **Caddy** on 80/443 with automatic TLS for `OAMS_DOMAIN`

### 5.3 HTTPS

TLS is terminated by the Compose `caddy` service (`deploy/Caddyfile`). No separate host proxy is required unless you already have one.

### 5.4 Nightly finalize job

After shift end (IST), run:

```bash
docker compose -f docker-compose.prod.yml --env-file .env --profile worker run --rm worker
```

Or HTTP:

```bash
curl -X POST "https://your-host/api/internal/finalize-day" \
  -H "X-Cron-Secret: YOUR_INTERNAL_CRON_SECRET"
```

Cron example (20:30 Mon–Fri):

```cron
30 20 * * 1-5 cd /path/to/oams && docker compose -f docker-compose.prod.yml --env-file .env --profile worker run --rm worker
```

---

## 6. Office roll-out checklist

1. Sign in as **Admin**  
2. **Admin → Create kiosk** → copy pair code  
3. On door tablet open `https://your-host/kiosk/pair` → enter code  
4. Leave tablet on `/kiosk` (fullscreen / kiosk mode)  
5. Employees open `/punch` → allow camera → Add to Home Screen  
6. **Admin → Create display URL** → open on TV fullscreen  
7. Import staff via CSV (`sample_employees.csv` format):  
   `name,email,role,team,password`  
8. Set shift times / grace / holidays under **Admin**  
9. Schedule finalize worker (section 5.4)

---

## 7. Useful commands

```bash
# Health
curl http://localhost:8000/api/health

# API docs
open http://localhost:8000/docs

# Dev logs
docker compose logs -f api

# Run migrations manually (from backend/)
alembic upgrade head

# Unit tests
cd backend && pytest -q

# Finalize today (local)
cd backend && python -m app.worker
```

---

## 8. Configuration reference

| Variable | Default (dev) | Purpose |
|----------|---------------|---------|
| `DATABASE_URL` | SQLite file | DB connection |
| `SECRET_KEY` | dev value | JWT signing |
| `QR_HMAC_SECRET` | dev value | Door QR signing |
| `INTERNAL_CRON_SECRET` | dev value | Finalize auth |
| `AUTO_CREATE_SCHEMA` | `true` | `create_all` on startup (dev only) |
| `RUN_SEED_ON_STARTUP` | `true` | Seed demo users |
| `CORS_ORIGINS` | `*` | Allowed browser origins |
| `APP_NAME` | `OAMS Office` | Display / seed name |
| `SEED_ADMIN_EMAIL` | `admin@office.local` | First admin |
| `SEED_ADMIN_PASSWORD` | `admin123` | First admin password |

See [`.env.example`](.env.example).

---

## 9. Troubleshooting

| Problem | Fix |
|---------|-----|
| `docker.sock` / daemon error | Start Docker Desktop or `sudo systemctl start docker` |
| Port 8000 in use | Stop other process or change compose ports |
| Camera blocked on `/punch` | Use HTTPS or localhost; allow camera permission |
| Kiosk unauthorized | Re-create pair code in Admin; pair again at `/kiosk/pair` |
| TV page 404 | Display token is shown **once** — create a new token |
| Prod migrate fails | Check `POSTGRES_PASSWORD` and DB health |
| Empty wallboard | Punch people in first; wallboard reads precomputed attendance |

---

## 10. Next reading

- [README.md](README.md) — product overview  
- [BUILD.md](BUILD.md) — deeper build notes  
- [ARCHITECTURE.md](ARCHITECTURE.md) — code layers  
- [ROADMAP.md](ROADMAP.md) — upcoming work  
