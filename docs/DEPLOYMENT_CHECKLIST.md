# Deployment Checklist

## Pre-deployment

- [ ] Copy `.env.example` to `.env` and fill all production values
- [ ] Generate API keys: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- [ ] Generate webhook secret: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- [ ] Set `APP_ENV=production`
- [ ] Set `CORS_ORIGINS` to your actual frontend domain(s)
- [ ] Set `ENABLE_AUTOPUBLISH=true` only when publishing webhook is tested
- [ ] Run tests locally: `pytest tests/ -v`

## Database

- [ ] For production: switch `DATABASE_URL` to PostgreSQL
- [ ] Run initial migration: `alembic upgrade head`
- [ ] Verify tables exist: hit `GET /system/health` and confirm `database: ok`

## Security

- [ ] `API_KEYS` is set (non-empty) — endpoints require `X-API-Key` header
- [ ] `WEBHOOK_SECRET` is set for inbound webhook HMAC verification
- [ ] HTTPS is enforced at the reverse proxy / platform level
- [ ] `CORS_ORIGINS` does NOT contain `*` in production
- [ ] Rate limiting is active (default 60 req/min per IP)

## Platform-specific

### Render
- [ ] Push repo → auto-deploys from `render.yaml`
- [ ] Set env vars in Render dashboard (secrets tab)
- [ ] Health check path is `/system/health`

### Railway
- [ ] Push repo → auto-deploys from `railway.toml`
- [ ] Set env vars in Railway dashboard
- [ ] Health check path is `/system/health`

### Docker / VPS
- [ ] Build: `docker compose build`
- [ ] Run: `docker compose up -d`
- [ ] Set up reverse proxy (nginx/caddy) with HTTPS
- [ ] Set up log rotation for container logs
- [ ] Set up monitoring/alerting on `/system/health`

## Post-deployment verification

- [ ] `GET /` returns `{"status": "ok"}`
- [ ] `GET /system/health` returns `{"status": "ok", "database": "ok"}`
- [ ] `GET /docs` loads the Swagger UI
- [ ] `POST /system/bootstrap` returns success
- [ ] Full pipeline test:
  1. `POST /content/generate-calendar` with `{"days": 3}`
  2. `POST /content/generate-assets` with `{}`
  3. `POST /distribution/queue` with `{"only_status": "draft"}`
  4. `POST /distribution/publish` with `{"limit": 50}`
  5. `POST /analytics/simulate`
  6. `GET /analytics/summary`
  7. `GET /optimizer/recommendations`

## Webhook integrations (when ready)

- [ ] Set `AI_WEBHOOK_URL` and `AI_WEBHOOK_TOKEN` to your AI generation endpoint
- [ ] Test with `POST /content/generate-assets` — verify AI-generated copy appears
- [ ] Set `PUBLISH_WEBHOOK_URL` and `PUBLISH_WEBHOOK_TOKEN` to your publishing tool
- [ ] Test with `POST /distribution/publish` — verify posts appear on the target platform
- [ ] Set `ENABLE_AUTOPUBLISH=true` after publish webhook is verified
- [ ] See `docs/WEBHOOK_CONTRACTS.md` for payload schemas
