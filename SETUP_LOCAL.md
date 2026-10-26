# OAMS — Setup Without Docker

Install and run OAMS on a laptop/server using **Python + SQLite** (or local Postgres). No Docker required.

---

## 1. Prerequisites

| Software | Version | Notes |
|----------|---------|-------|
| Python | **3.10+** (3.12 recommended) | `python3 --version` |
| pip | bundled with Python | `python3 -m pip --version` |
| venv | `python3-venv` on Debian/Ubuntu | `sudo apt install python3-venv python3-pip` |
| Git | any | optional |
| Browser | Chrome / Edge / Firefox | for UI + camera punch |

**Optional (production-like local DB):** PostgreSQL 14+ and `psycopg2-binary` (already in requirements).

---

## 2. One-command setup (recommended)

From the `oams/` folder:

```bash
chmod +x scripts/setup_local.sh
./scripts/setup_local.sh
```

This will:

1. Create `backend/.venv`
2. Install packages from `requirements.txt`
3. Copy `.env.local.example` → `backend/.env` (if missing)
4. Print how to start the server

Then start:

```bash
./scripts/run_local.sh
```

Open **http://localhost:8000**

---

## 3. Manual setup (step by step)

### 3.1 Go to the project

```bash
cd oams
```

### 3.2 Create a virtual environment

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
# Windows (PowerShell):
# .\.venv\Scripts\Activate.ps1
```

### 3.3 Install dependencies

Use the root requirements file (same packages as Docker):

```bash
# from oams/backend with venv active:
pip install --upgrade pip
pip install -r ../requirements.txt
```

Or:

```bash
pip install -r requirements.txt
```

(`oams/requirements.txt` and `oams/backend/requirements.txt` are kept in sync.)

### 3.4 Configure environment

```bash
# from oams/
cp .env.local.example backend/.env
```

Default local settings use **SQLite** (`oams.db` created on first run).

### 3.5 Run the API

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3.6 Verify

```bash
curl http://localhost:8000/api/health
```

Browser: http://localhost:8000  

API docs: http://localhost:8000/docs

---

## 4. Demo logins

Seeded automatically when `RUN_SEED_ON_STARTUP=true`:

| Role | Email | Password |
|------|-------|----------|
| Admin | `admin@office.local` | `admin123` |
| Manager | `manager@office.local` | `manager123` |
| Employee | `employee@office.local` | `employee123` |

---

## 5. Using local Postgres (optional)

1. Install and start Postgres.
2. Create DB/user:

```sql
CREATE USER oams WITH PASSWORD 'oams_secret';
CREATE DATABASE oams OWNER oams;
```

3. Edit `backend/.env`:

```env
DATABASE_URL=postgresql+psycopg2://oams:oams_secret@localhost:5432/oams
AUTO_CREATE_SCHEMA=false
```

4. Run migrations:

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
```

5. Start uvicorn as above. Set `RUN_SEED_ON_STARTUP=true` once to create the admin user.

---

## 6. Tests

```bash
cd backend
source .venv/bin/activate
pytest -q
```

---

## 7. Finalize-day job (no Docker)

```bash
cd backend
source .venv/bin/activate
python -m app.worker
# specific date:
python -m app.worker --date 2026-08-03
```

Or HTTP:

```bash
curl -X POST "http://localhost:8000/api/internal/finalize-day" \
  -H "X-Cron-Secret: change-me-cron-secret"
```

(Use the same secret as `INTERNAL_CRON_SECRET` in `.env`.)

---

## 8. Office devices (same as Docker install)

1. Admin → Create kiosk → pair tablet at `/kiosk/pair`
2. Employees punch at `/punch` (camera; prefer HTTPS off-localhost)
3. Admin → Create TV display URL → open `/display/{token}` fullscreen

---

## 9. Troubleshooting

| Issue | Fix |
|-------|-----|
| `ensurepip` / venv fails | `sudo apt install python3-venv python3-pip` |
| `pip` not found | `python3 -m ensurepip --upgrade` or install `python3-pip` |
| Port 8000 busy | `--port 8080` or stop the other process |
| Camera blocked | Use `localhost` or HTTPS |
| Import errors | Confirm venv is active and you run from `backend/` |
| DB locked (SQLite) | Stop other uvicorn processes using `oams.db` |

---

## 10. Related docs

| File | Content |
|------|---------|
| [README.md](README.md) | Product overview |
| [SETUP.md](SETUP.md) | Full setup (Docker + local summary) |
| [DOCS.md](DOCS.md) | Documentation index |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Code layers |
| [requirements.txt](requirements.txt) | Python packages |
