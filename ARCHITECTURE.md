# Architecture overview for OAMS

## Layers

```
factory.py / main.py  → Application Factory (create_app)
bootstrap/            → env profile + startup validators (Strategy/Composite) + Facade
routers/              → HTTP adapters only
container.py          → request-scoped DI
application/          → use-case services
domain/               → policies + ports
infrastructure/       → SQLAlchemy UoW / repos + security headers middleware
alembic/              → schema migrations
worker.py             → finalize-day job entrypoint
deploy/Caddyfile      → TLS edge (prod Compose)
```

## Key design choices

- **Write path:** punch / leave / correction update `attendance_days` via policy
- **Read path (TV):** wallboard reads precomputed `attendance_days` + last punch (no re-derive)
- **Jobs:** `job_runs` table makes finalize-day idempotent
- **Punches:** optional `Idempotency-Key` header; QR nonce still one-time
- **Concurrency:** `attendance_days.version` + `SELECT FOR UPDATE` on Postgres derive

## Extending attendance rules

Inject `PresenceStatusRule` implementations into `DefaultAttendancePolicy`, or replace `get_policy()` in `container.py`.

## Ops

- Dev: `AUTO_CREATE_SCHEMA=true` (default); docs on; SQLite OK
- Prod: `APP_ENV=production` → validators enforce Postgres, Alembic-only, strong secrets, explicit CORS, no seed; docs off; Caddy terminates TLS (`DEPLOYMENT.md`)
- Finalize: `python -m app.worker` or `POST /api/internal/finalize-day`
