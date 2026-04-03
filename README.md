# POLITMATRADER AI Marketing System

A production-ready FastAPI backend that automates social media content generation, scheduling, distribution, and performance optimization for [PolitmaTrader.com](https://politmatrader.com).

## What it does

- Generates a rolling 30-day content calendar weighted by pillar (education 40%, authority 30%, promotion 20%, lifestyle 10%)
- Creates platform-specific assets for Instagram, TikTok, YouTube, X, Facebook, and LinkedIn
- Repurposes content across platforms (YouTube → X threads + LinkedIn, Instagram → Facebook + TikTok)
- Queues posts with platform-optimal scheduling times
- Publishes via webhook to Buffer, Metricool, Hootsuite, or any custom endpoint
- Tracks analytics and generates optimization recommendations
- Runs a daily automated pipeline via APScheduler

## Stack

- **FastAPI** — async HTTP framework with auto-generated OpenAPI docs
- **SQLAlchemy 2.0** — ORM with SQLite (dev) or PostgreSQL (production)
- **APScheduler** — cron-based daily automation
- **httpx** — outbound webhook client with timeout/retry
- **Alembic** — database migrations
- **Gunicorn + Uvicorn** — production ASGI server
- **Docker** — containerized deployment

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your values
uvicorn app.main:app --reload
```

Open:
- API root: `http://127.0.0.1:8000`
- Swagger docs: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## API flow

```
POST /system/bootstrap
POST /content/generate-calendar    {"days": 30}
POST /content/generate-assets      {}
POST /distribution/queue           {"only_status": "draft"}
POST /distribution/publish         {"limit": 50}
POST /analytics/simulate
GET  /analytics/summary
GET  /optimizer/recommendations
```

Or run the entire pipeline in one call:

```
POST /system/daily-run
```

## Project structure

```
├── app/
│   ├── main.py              # App entrypoint, middleware, lifespan
│   ├── config.py             # Pydantic settings with validation
│   ├── db.py                 # Engine, session factory, get_db dependency
│   ├── models.py             # SQLAlchemy ORM models
│   ├── schemas.py            # Pydantic request/response schemas
│   ├── brand.py              # Platform profiles, topic bank, content mix
│   ├── middleware/            # API key auth, rate limiting, webhook signatures
│   ├── routers/              # Route modules (system, content, distribution, analytics, optimizer)
│   └── services/             # Business logic (content, distribution, analytics, optimizer, providers)
├── tests/                    # pytest test suite (15 tests)
├── alembic/                  # Database migration scripts
├── docs/
│   ├── DEPLOYMENT_CHECKLIST.md
│   └── WEBHOOK_CONTRACTS.md
├── Dockerfile
├── docker-compose.yml
├── Procfile                  # Render / Railway
├── render.yaml               # Render blueprint
├── railway.toml              # Railway config
└── requirements.txt
```

## Security

- **API key authentication** — set `API_KEYS` in `.env`; all mutating endpoints require `X-API-Key` header
- **Rate limiting** — 60 requests/minute per IP (configurable via `RATE_LIMIT_PER_MINUTE`)
- **Webhook signature verification** — HMAC-SHA256 for inbound webhooks via `WEBHOOK_SECRET`
- **CORS** — restricted to configured origins
- **Non-root Docker user** — container runs as `appuser`
- **Global exception handler** — internal errors never leak stack traces

## Deployment

See `docs/DEPLOYMENT_CHECKLIST.md` for the full checklist.

**Docker:**
```bash
docker compose up -d
```

**Render:** Push to GitHub → auto-deploys from `render.yaml`.

**Railway:** Push to GitHub → auto-deploys from `railway.toml`.

## Webhook integrations

The system works standalone with built-in rule-based content and simulated publishing. When ready for real integrations:

1. Set `AI_WEBHOOK_URL` / `AI_WEBHOOK_TOKEN` for LLM-powered content generation
2. Set `PUBLISH_WEBHOOK_URL` / `PUBLISH_WEBHOOK_TOKEN` for social publishing

See `docs/WEBHOOK_CONTRACTS.md` for exact JSON payload schemas.

## Running tests

```bash
pytest tests/ -v
```

## License

Proprietary — PolitmaTrader.com
