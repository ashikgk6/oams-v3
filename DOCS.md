# OAMS documentation index

| Document | When to read it |
|----------|-----------------|
| [README.md](README.md) | Start here — what OAMS is and quick links |
| [SETUP_LOCAL.md](SETUP_LOCAL.md) | **Build & run without Docker** (Python + SQLite) |
| [SETUP.md](SETUP.md) | Full setup (Docker + production + hardware) |
| [DEPLOYMENT.md](DEPLOYMENT.md) | **Production** Compose + Caddy TLS + security checklist |
| [BUILD.md](BUILD.md) | Extra build / verify / troubleshoot notes |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Code layers, SOLID, scalability |
| [ROADMAP.md](ROADMAP.md) | Implemented vs planned work |
| [requirements.txt](requirements.txt) | Python package list (no Docker) |

## Scripts

| Script | Purpose |
|--------|---------|
| [`scripts/setup_local.sh`](scripts/setup_local.sh) | Create venv + install requirements |
| [`scripts/run_local.sh`](scripts/run_local.sh) | Start API on port 8000 |
| [`scripts/finalize_cron.sh`](scripts/finalize_cron.sh) | Call finalize-day over HTTP |

## Config samples

| File | Purpose |
|------|---------|
| [`.env.local.example`](.env.local.example) | Local SQLite env (no Docker) |
| [`.env.example`](.env.example) | Docker / Postgres / general env |
| [`.env.production.example`](.env.production.example) | Production secrets + domain / CORS |
