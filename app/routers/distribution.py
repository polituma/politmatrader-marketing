"""
Distribution routes: queue and publish.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..middleware import require_api_key
from ..schemas import MessageOut, PublishRequest, QueueRequest
from ..services.distribution import DistributionService

router = APIRouter(prefix="/distribution", tags=["distribution"])

distribution = DistributionService()


@router.post("/queue", response_model=MessageOut, dependencies=[Depends(require_api_key)])
def queue_posts(request: QueueRequest):
    rows = distribution.queue_posts(
        date_from=request.date_from,
        date_to=request.date_to,
        only_status=request.only_status,
    )
    return MessageOut(ok=True, detail={"queued": len(rows)})


@router.post("/publish", response_model=MessageOut, dependencies=[Depends(require_api_key)])
def publish_posts(request: PublishRequest):
    rows = distribution.publish_due_posts(limit=request.limit)
    return MessageOut(ok=True, detail={"published": len(rows)})
