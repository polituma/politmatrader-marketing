"""
Analytics: ingest real metrics, simulate test data, produce summaries.
"""

from __future__ import annotations

import logging
import random

from fastapi import HTTPException
from sqlalchemy import select

from ..db import SessionLocal
from ..models import ContentAssetDB, PerformanceRecordDB
from ..schemas import PerformanceIngestRequest, SummaryOut

logger = logging.getLogger("politma.analytics")


class AnalyticsService:
    def ingest(self, payload: PerformanceIngestRequest) -> PerformanceRecordDB:
        with SessionLocal() as session:
            asset = session.get(ContentAssetDB, payload.asset_id)
            if not asset:
                raise HTTPException(status_code=404, detail="Asset not found")

            record = PerformanceRecordDB(
                asset_id=payload.asset_id,
                platform=payload.platform,
                impressions=payload.impressions,
                clicks=payload.clicks,
                engagements=payload.engagements,
                conversions=payload.conversions,
                spend=payload.spend,
            )
            session.add(record)
            session.commit()
            session.refresh(record)

            logger.info(
                "Ingested metrics for asset %s on %s",
                payload.asset_id,
                payload.platform,
            )
            return record

    def simulate_for_published(self) -> int:
        """Create fake analytics rows for all published assets (dev/demo use)."""
        with SessionLocal() as session:
            assets = (
                session.execute(
                    select(ContentAssetDB).where(
                        ContentAssetDB.status == "published"
                    )
                )
                .scalars()
                .all()
            )

            count = 0
            for asset in assets:
                # Don't double-simulate: skip if a record already exists
                existing = session.execute(
                    select(PerformanceRecordDB).where(
                        PerformanceRecordDB.asset_id == asset.id
                    )
                ).scalars().first()
                if existing:
                    continue

                impressions = random.randint(1_000, 20_000)
                clicks = random.randint(20, min(900, impressions))
                engagements = random.randint(50, min(1_800, impressions))

                session.add(
                    PerformanceRecordDB(
                        asset_id=asset.id,
                        platform=asset.platform,
                        impressions=impressions,
                        clicks=clicks,
                        engagements=engagements,
                        conversions=random.randint(0, min(40, clicks)),
                        spend=0.0,
                    )
                )
                count += 1

            session.commit()
            logger.info("Simulated analytics for %d assets", count)
            return count

    def summary(self) -> SummaryOut:
        with SessionLocal() as session:
            rows = session.execute(select(PerformanceRecordDB)).scalars().all()

        total_impressions = sum(r.impressions for r in rows)
        total_clicks = sum(r.clicks for r in rows)
        total_engagements = sum(r.engagements for r in rows)
        total_conversions = sum(r.conversions for r in rows)

        return SummaryOut(
            total_assets=len(set(r.asset_id for r in rows)),
            total_impressions=total_impressions,
            total_clicks=total_clicks,
            total_engagements=total_engagements,
            total_conversions=total_conversions,
            avg_ctr=(
                round((total_clicks / total_impressions) * 100, 2)
                if total_impressions
                else 0.0
            ),
            avg_engagement_rate=(
                round((total_engagements / total_impressions) * 100, 2)
                if total_impressions
                else 0.0
            ),
            avg_conversion_rate=(
                round((total_conversions / total_clicks) * 100, 2)
                if total_clicks
                else 0.0
            ),
        )
