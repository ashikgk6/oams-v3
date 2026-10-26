# OAMS — Office Attendance Monitoring System

In-office attendance for Indian startups (~150 people).

Employees scan a **rotating QR** on a door tablet to punch IN/OUT. Managers use a web dashboard. A reception **TV** shows who is in the office.

---

## Documentation

| File | Purpose |
|------|---------|
| **[SETUP_LOCAL.md](SETUP_LOCAL.md)** | Setup **without Docker** (Python + SQLite) |
| **[SETUP.md](SETUP.md)** | Full setup (Docker, production, office hardware) |
| **[DEPLOYMENT.md](DEPLOYMENT.md)** | Production Compose + Caddy TLS |
| **[DOCS.md](DOCS.md)** | Index of all docs |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Architecture notes |
| [ROADMAP.md](ROADMAP.md) | Roadmap |
| [requirements.txt](requirements.txt) | Python dependencies |

---

## Quick start — without Docker

```bash
cd oams
chmod +x scripts/setup_local.sh scripts/run_local.sh
./scripts/setup_local.sh
./scripts/run_local.sh
```

Open **http://localhost:8000**

| Role | Email | Password |
|------|-------|----------|
| Admin | `admin@office.local` | `admin123` |
| Manager | `manager@office.local` | `manager123` |
| Employee | `employee@office.local` | `employee123` |

---

## Quick start — with Docker

```bash
cd oams
docker compose up --build
```

Open **http://localhost:8000**

---

## What it does

- Door kiosk with short-lived signed QR
- Phone punch PWA (camera scan)
- Present / Late / Absent / On leave / Half-day (IST)
- Leave (CL / SL / EL) + corrections + approvals
- TV wallboard (`/display/{token}`)
- CSV import + monthly export
- Finalize job (`python -m app.worker`)

---

## Stack

- **API:** FastAPI (Python 3.10+)
- **DB:** SQLite (local) or Postgres (Docker/production)
- **UI:** Static PWA (no Node.js)
- **Deps:** [`requirements.txt`](requirements.txt)

---

## Main URLs

| Path | Use |
|------|-----|
| `/login` | Sign in |
| `/dashboard` | Today’s attendance |
| `/punch` | Employee QR scan |
| `/kiosk` / `/kiosk/pair` | Door tablet |
| `/admin` | Settings, kiosk, TV, CSV, reports |
| `/display/{token}` | TV wallboard |
| `/api/health` | Health check |
| `/docs` | Swagger |

---

## Project layout

```
oams/
├── README.md
├── SETUP_LOCAL.md          # No-Docker setup
├── SETUP.md
├── DOCS.md
├── requirements.txt        # pip packages
├── .env.local.example
├── scripts/
│   ├── setup_local.sh
│   ├── run_local.sh
│   └── finalize_cron.sh
└── backend/
    ├── requirements.txt    # same packages
    ├── alembic/
    ├── tests/
    └── app/
```

---

## License / note

Internal template. Change default passwords and secrets before real office use.
