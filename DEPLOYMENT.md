# Production deployment (OAMS)

## Architecture (edge)

```
Internet → Caddy (:80/:443, TLS) → api:8000 (internal Docker network)
                ↘ db:5432 (internal only; not published)
```

- **Factory:** `app.factory.create_app()` builds FastAPI (docs off in prod).
- **Facade:** `ApplicationBootstrap` runs schema/seed after validators.
- **Strategy + Composite:** startup validators refuse weak secrets, SQLite, `create_all`, wildcard CORS, and demo seeding in strict production.

## Prerequisites

- DNS A/AAAA for `OAMS_DOMAIN` pointing at the host
- Ports 80/443 reachable (Let's Encrypt via Caddy)
- Docker + Compose v2

## Steps

1. Copy env template and edit secrets:

```bash
cp .env.production.example .env
# set OAMS_DOMAIN, CORS_ORIGINS, POSTGRES_PASSWORD, SECRET_KEY, QR_HMAC_SECRET, INTERNAL_CRON_SECRET
```

2. Generate secrets:

```bash
openssl rand -hex 32   # SECRET_KEY
openssl rand -hex 32   # QR_HMAC_SECRET
openssl rand -hex 32   # INTERNAL_CRON_SECRET
openssl rand -hex 24   # POSTGRES_PASSWORD
```

3. Start (migrate runs once before API):

```bash
docker compose -f docker-compose.prod.yml --env-file .env up -d --build
```

4. Health check (through the proxy):

```bash
curl -fsS "https://$OAMS_DOMAIN/api/health"
```

5. Create the first admin **out-of-band** (strict prod blocks `RUN_SEED_ON_STARTUP`). Options:
   - Temporarily run a staging profile with seed, then promote DB; or
   - Insert a hashed user via a one-off management script against the DB network.

6. Optional finalize-day worker (one-shot profile):

```bash
docker compose -f docker-compose.prod.yml --env-file .env --profile worker run --rm worker
```

Schedule that with host cron (e.g. 23:30 IST) or call `POST /api/internal/finalize-day` with `X-Cron-Secret`.

## Security checklist

| Control | Expected |
|---------|----------|
| `APP_ENV` | `production` |
| `ENABLE_DOCS` | `false` (`/docs` unavailable) |
| `CORS_ORIGINS` | Exact public origin(s), no `*` |
| `AUTO_CREATE_SCHEMA` | `false` (Alembic only) |
| `RUN_SEED_ON_STARTUP` | `false` |
| Secrets | ≥24 chars, not placeholders |
| DB / API ports | Not published; only Caddy |

If boot fails with `ConfigurationError`, fix `.env` — the process is designed to refuse unsafe production config.

## Rollback

```bash
docker compose -f docker-compose.prod.yml --env-file .env down
# restore Postgres volume backup, then re-up previous image tag
```

## Related

- [ARCHITECTURE.md](ARCHITECTURE.md) — layers and SOLID
- [SETUP.md](SETUP.md) — broader ops / hardware
- [DOCS.md](DOCS.md) — doc index
