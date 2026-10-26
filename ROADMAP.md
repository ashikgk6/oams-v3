# Architecture implementation roadmap for OAMS

## Done (this iteration)

- [x] Alembic migrations (`backend/alembic`)
- [x] Production compose (`docker-compose.prod.yml`) — no reload, migrate job, workers
- [x] Non-root Dockerfile user
- [x] All routers go through application services (no dual write path)
- [x] Attendance policy unit tests
- [x] Punch `(user_id, ts)` index + `idempotency_key`
- [x] Attendance day `version` + `SELECT FOR UPDATE` on derive (Postgres)
- [x] Wallboard **read model** (no re-derive on poll)
- [x] Idempotent finalize via `job_runs` + `python -m app.worker`
- [x] Application Factory + bootstrap validators (secrets/SQLite/CORS/schema/seed)
- [x] Prod edge: Caddy HTTPS; API/DB not published; docs disabled
- [x] `DEPLOYMENT.md` + `.env.production.example`

## Next (Phase C)

- [ ] Google/Microsoft SSO
- [ ] `office_id` / multi-office filter on core tables
- [ ] Redis cache in front of wallboard (5–10s TTL)
- [ ] Kiosk offline punch queue (store & forward)
- [ ] OpenAPI-generated typed client / Vite frontend
- [ ] Structured logging + Prometheus metrics
