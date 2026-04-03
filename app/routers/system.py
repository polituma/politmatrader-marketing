"""
System routes: health check, bootstrap, daily orchestration.
"""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends

from ..config import settings
from ..middleware import require_api_key
from ..schemas import BootstrapResponse, HealthResponse, MessageOut
from ..services.analytics import AnalyticsService
from ..services.content import ContentCreatorService, ContentStrategistService, RepurposingService
from ..services.distribution import DistributionService

logger = logging.getLogger("politma.routes.system")

router = APIRouter(prefix="/system", tags=["system"])

strategist = ContentStrategistService()
creator = ContentCreatorService()
repurposer = RepurposingService()
distribution = DistributionService()


@router.get("/health", response_model=HealthResponse)
def health_check():
    """Liveness / readiness probe for Render, Railway, or load balancers."""
    from ..db import SessionLocal

    db_status = "ok"
    try:
        with SessionLocal() as session:
            session.execute("SELECT 1" if False else __import__("sqlalchemy").text("SELECT 1"))
    except Exception:
        db_status = "degraded"

    return HealthResponse(
        status="ok",
        environment=settings.app_env,
        database=db_status,
        scheduler="enabled" if settings.enable_autopublish else "standby",
    )


@router.post("/bootstrap", response_model=BootstrapResponse)
def system_bootstrap():
    return BootstrapResponse(
        ok=True,
        message="POLITMATRADER production marketing system initialized.",
        version="1.0.0",
    )


@router.post("/daily-run", response_model=MessageOut, dependencies=[Depends(require_api_key)])
def system_daily_run():
    """
    Full pipeline: calendar → assets → repurpose → queue → publish.
    Called by the scheduler or manually via API.
    """
    today = datetime.now().strftime("%Y-%m-%d")

    created_calendar = strategist.generate_calendar(
        days=30, start_date=today, clear_existing=False
    )
    created_assets = creator.generate_assets(
        date_from=today, date_to=None, overwrite_existing=False
    )
    repurposed_assets = repurposer.repurpose()
    queued_items = distribution.queue_posts(
        date_from=today, date_to=None, only_status="draft"
    )
    published_items = (
        distribution.publish_due_posts(limit=100)
        if settings.enable_autopublish
        else []
    )

    result = {
        "calendar_items": len(created_calendar),
        "created_assets": len(created_assets),
        "repurposed_assets": len(repurposed_assets),
        "queued_items": len(queued_items),
        "published_items": len(published_items),
    }
    logger.info("Daily run complete: %s", result)
    return MessageOut(ok=True, detail=result)
