"""
Content routes: calendar generation, asset creation.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends

from ..middleware import require_api_key
from ..models import ContentAssetDB
from ..schemas import (
    AssetOut,
    CalendarIdeaOut,
    GenerateAssetsRequest,
    GenerateCalendarRequest,
)
from ..services.content import ContentCreatorService, ContentStrategistService, RepurposingService

router = APIRouter(prefix="/content", tags=["content"])

strategist = ContentStrategistService()
creator = ContentCreatorService()
repurposer = RepurposingService()


def _asset_to_out(row: ContentAssetDB) -> AssetOut:
    return AssetOut(
        id=row.id,
        date=row.date,
        platform=row.platform,
        format=row.format,
        pillar=row.pillar,
        topic=row.topic,
        hook=row.hook,
        body=row.body,
        cta=row.cta,
        hashtags=json.loads(row.hashtags) if isinstance(row.hashtags, str) else row.hashtags,
        visual_brief=row.visual_brief,
        status=row.status,
        source_asset_id=row.source_asset_id,
    )


@router.post(
    "/generate-calendar",
    response_model=list[CalendarIdeaOut],
    dependencies=[Depends(require_api_key)],
)
def generate_calendar(request: GenerateCalendarRequest):
    rows = strategist.generate_calendar(
        days=request.days,
        start_date=request.start_date,
        clear_existing=request.clear_existing,
    )
    return [
        CalendarIdeaOut(
            id=row.id,
            date=row.date,
            pillar=row.pillar,
            topic=row.topic,
            angle=row.angle,
            target_platforms=json.loads(row.target_platforms),
            campaign_tag=row.campaign_tag,
        )
        for row in rows
    ]


@router.post(
    "/generate-assets",
    response_model=list[AssetOut],
    dependencies=[Depends(require_api_key)],
)
def generate_assets(request: GenerateAssetsRequest):
    rows = creator.generate_assets(
        date_from=request.date_from,
        date_to=request.date_to,
        overwrite_existing=request.overwrite_existing,
    )
    rows.extend(repurposer.repurpose())
    return [_asset_to_out(row) for row in rows]
