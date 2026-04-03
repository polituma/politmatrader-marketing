"""
POLITMATRADER AI Marketing System — Application entrypoint.

Changes from original:
- Replaced deprecated @app.on_event with lifespan context manager
- Added CORS middleware
- Added request-ID middleware for log tracing
- Added rate-limiting middleware
- Routers are cleanly separated
- Global exception handler prevents secret leakage
"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from apscheduler.schedulers.background import BackgroundScheduler

from .config import settings
from .db import Base, engine
from .middleware import rate_limiter
from .routers import analytics, content, distribution, optimizer, system

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("politma")

# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------
scheduler = BackgroundScheduler(timezone=settings.default_timezone)


def _scheduled_daily_run():
    """Invoked by APScheduler; imports the route handler lazily."""
    try:
        logger.info("Starting scheduled daily run")
        from .routers.system import system_daily_run

        system_daily_run()
        logger.info("Scheduled daily run complete")
    except Exception:
        logger.exception("Scheduled daily run failed")


# ---------------------------------------------------------------------------
# Lifespan (replaces deprecated on_event)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ensured")

    scheduler.add_job(
        _scheduled_daily_run,
        "cron",
        hour=settings.scheduler_daily_hour,
        minute=settings.scheduler_daily_minute,
        id="daily_run",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        "Scheduler started — daily run at %02d:%02d %s",
        settings.scheduler_daily_hour,
        settings.scheduler_daily_minute,
        settings.default_timezone,
    )
    logger.info("POLITMATRADER Marketing System ready [%s]", settings.app_env)

    yield

    # Shutdown
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
app = FastAPI(
    title="POLITMATRADER AI Marketing System",
    version="1.0.0",
    description=(
        "Automated social-media content generation, scheduling, "
        "and optimization for PolitmaTrader.com"
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Attach a unique request ID to every request for log correlation."""
    request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex[:12])
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
    response.headers["X-Request-ID"] = request_id
    logger.debug(
        "%s %s → %s (%sms) [%s]",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
        request_id,
    )
    return response


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Enforce per-IP rate limiting."""
    client_ip = request.client.host if request.client else "unknown"
    if not rate_limiter.check(client_ip):
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Try again shortly."},
        )
    return await call_next(request)


# ---------------------------------------------------------------------------
# Global exception handler — never leak internals
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(system.router)
app.include_router(content.router)
app.include_router(distribution.router)
app.include_router(analytics.router)
app.include_router(optimizer.router)


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------
@app.get("/", tags=["root"])
def root():
    return {
        "app": "POLITMATRADER AI Marketing System",
        "version": "1.0.0",
        "status": "ok",
        "environment": settings.app_env,
        "docs": f"{settings.base_url}/docs",
    }
