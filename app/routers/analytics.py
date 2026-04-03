"""
Analytics routes: ingest, simulate, summary.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..middleware import require_api_key
from ..schemas import MessageOut, PerformanceIngestRequest, SummaryOut
from ..services.analytics import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])

analytics = AnalyticsService()


@router.post("/ingest", response_model=MessageOut, dependencies=[Depends(require_api_key)])
def ingest_metrics(request: PerformanceIngestRequest):
    row = analytics.ingest(request)
    return MessageOut(ok=True, detail={"record_id": row.id})


@router.post("/simulate", response_model=MessageOut, dependencies=[Depends(require_api_key)])
def simulate_metrics():
    count = analytics.simulate_for_published()
    return MessageOut(ok=True, detail={"created_records": count})


@router.get("/summary", response_model=SummaryOut, dependencies=[Depends(require_api_key)])
def analytics_summary():
    return analytics.summary()
