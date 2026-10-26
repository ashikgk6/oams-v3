# OAMS — Build Process

Step-by-step instructions to build, run, and verify the Office Attendance Monitoring System.

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Docker + Docker Compose | 20+ / v2 | Recommended production-like run |
| **or** Python | 3.10+ | Local development without Docker |
| Git | any | Clone / pull the repo |
| Modern browser | Chrome / Edge / Firefox | Admin UI, punch PWA, TV display |

Optional for office hardware:

- Android tablet (door kiosk)
- TV / monitor + Fire Stick / Android box / spare PC (wallboard)

---

## Option A — Build & run with Docker (recommended)

### Production

```bash
cp .env.example .env
# set POSTGRES_PASSWORD, SECRET_KEY, QR_HMAC_SECRET, INTERNAL_CRON_SECRET
docker compose -f docker-compose.prod.yml up --build -d
```

Migrations run in the `migrate` service before API starts.

Finalize worker (cron-friendly):

```bash
docker compose -f docker-compose.prod.yml --profile worker run --rm worker
# or locally:
cd backend && python -m app.worker --date 2026-08-03
```

### Tests

```bash
cd backend
pip install -r requirements.txt
pytest -q
```

### 1. Go to the project folder

```bash
cd oams
```

### 2. (Optional) Set secrets

Copy the example env file and edit secrets before production use:

```bash
cp .env.example .env
```

`docker-compose.yml` already injects defaults for local demo. For production, change:

- `SECRET_KEY`
- `QR_HMAC_SECRET`
- `INTERNAL_CRON_SECRET`
- `SEED_ADMIN_PASSWORD`
- Postgres password

### 3. Build images and start services

```bash
docker compose build
docker compose up -d
```

Or in one step:

```bash
docker compose up --build -d
```

What this builds:

1. Pulls `postgres:16-alpine`
2. Builds the API image from `backend/Dockerfile` (Python 3.12 + pip deps)
3. Starts `db` then `api` on port **8000**

### 4. Verify the build

```bash
docker compose ps
curl http://localhost:8000/api/health
```

Expected health response:

```json
{"status":"ok","app":"OAMS Office"}
```

Open the UI: [http://localhost:8000](http://localhost:8000)

### 5. Useful Docker commands

```bash
# Follow API logs
docker compose logs -f api

# Rebuild after dependency changes (requirements.txt / Dockerfile)
docker compose up --build -d

# Stop
docker compose down

# Stop and delete DB volume (wipes data)
docker compose down -v
```

---

## Option B — Build & run locally (SQLite, no Docker)

Use this for quick development on a laptop.

### 1. Create a virtual environment

```bash
cd oams/backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
```

### 2. Install dependencies (build step)

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure environment (optional)

By default the app uses SQLite file `oams.db` in the working directory.

For Postgres instead:

```bash
export DATABASE_URL="postgresql+psycopg2://oams:oams_secret@localhost:5432/oams"
export SECRET_KEY="change-me-in-production-use-long-random-string"
export QR_HMAC_SECRET="change-me-qr-hmac-secret-key"
export INTERNAL_CRON_SECRET="change-me-cron-secret"
```

### 4. Run the server

From `oams/backend`:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

On startup the app will:

1. Create database tables
2. Seed demo admin / manager / employee users
3. Seed IST office settings (09:30–18:30, 15 min grace)

### 5. Verify

```bash
curl http://localhost:8000/api/health
```

Open [http://localhost:8000](http://localhost:8000)

---

## Option C — Local API + Postgres (without full Compose for the API)

```bash
# Terminal 1 — database only
cd oams
docker compose up -d db

# Terminal 2 — API on host
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL="postgresql+psycopg2://oams:oams_secret@localhost:5432/oams"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Frontend “build”

There is **no Node/npm build**. The UI is static files served by FastAPI from:

```
backend/app/static/
  index.html          # SPA shell (login, dashboard, punch, admin, …)
  display.html        # TV wallboard
  assets/
    app.js
    styles.css
    manifest.json     # PWA
    sw.js             # service worker
    icon.svg
```

After changing JS/CSS, refresh the browser (hard refresh if the service worker cached assets).

---

## Post-build office checklist

1. Sign in as admin (`admin@office.local` / `admin123`)
2. **Admin → Create kiosk** → copy pair code
3. On door tablet open `/kiosk/pair` → enter code → leave `/kiosk` open
4. On phone open `/punch` → Add to Home Screen → scan QR
5. **Admin → Create display URL** → open on TV in fullscreen
6. Schedule daily finalize (after shift end, IST):

```bash
./scripts/finalize_cron.sh
# or:
curl -X POST "http://localhost:8000/api/internal/finalize-day" \
  -H "X-Cron-Secret: change-me-cron-secret"
```

Cron example (20:30 Mon–Fri):

```cron
30 20 * * 1-5 /path/to/oams/scripts/finalize_cron.sh
```

---

## Project layout (what gets built)

```
oams/
├── docker-compose.yml      # Orchestrates api + db
├── ARCHITECTURE.md         # SOLID layers & scalability
├── backend/
│   ├── Dockerfile          # API image build
│   ├── requirements.txt    # Python dependencies
│   └── app/                # Layered application source + static UI
├── scripts/
│   └── finalize_cron.sh    # Nightly attendance finalize
├── sample_employees.csv
├── BUILD.md                # This file
└── README.md
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Port 8000 in use | Change ports in `docker-compose.yml` or stop the other process |
| `docker.sock` / daemon error | Start Docker Desktop / `sudo systemctl start docker` |
| DB not ready | Wait for healthcheck; `docker compose logs db` |
| Camera blocked on `/punch` | Use HTTPS or `localhost`; allow camera permission |
| Kiosk “not authorized” | Re-create pair code in Admin and pair again at `/kiosk/pair` |
| TV page invalid | Display token is shown **once** on create — create a new token |
| Import CSV fails | Use UTF-8 CSV with columns `name,email,role,team,password` |

---

## Production build tips

1. Remove `--reload` from the Compose `command` (use the Dockerfile `CMD`).
2. Replace all default secrets.
3. Put the API behind HTTPS (Caddy / Nginx / cloud load balancer).
4. Back up the Postgres volume regularly.
5. Do not expose `/api/internal/*` without the cron secret (and prefer firewalling it).
