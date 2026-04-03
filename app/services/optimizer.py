"""
Optimization engine: generates actionable recommendations from performance data.
"""

from __future__ import annotations

import logging

from sqlalchemy import select

from ..config import settings
from ..db import SessionLocal
from ..models import PerformanceRecordDB, RecommendationDB
from ..schemas import RecommendationOut

logger = logging.getLogger("politma.optimizer")


class OptimizerService:
    def recommend(self) -> list[RecommendationOut]:
        with SessionLocal() as session:
            rows = session.execute(select(PerformanceRecordDB)).scalars().all()

            # Deactivate old recommendations
            session.query(RecommendationDB).update(
                {RecommendationDB.active: False}
            )

            if not rows:
                recs = [
                    RecommendationOut(
                        priority="high",
                        recommendation=(
                            "Connect live platform posting APIs and analytics "
                            "sources before making optimization decisions."
                        ),
                    ),
                    RecommendationOut(
                        priority="medium",
                        recommendation=(
                            "Add UTM tags and a campaign landing page for "
                            "POLITMATRADER social traffic."
                        ),
                    ),
                ]
            else:

                def ctr(x: PerformanceRecordDB) -> float:
                    return (
                        round((x.clicks / x.impressions) * 100, 2)
                        if x.impressions
                        else 0.0
                    )

                best = max(rows, key=ctr)
                worst = min(rows, key=ctr)
                recs = [
                    RecommendationOut(
                        priority="high",
                        recommendation=(
                            f"Scale creative patterns similar to asset "
                            f"{best.asset_id} on {best.platform}; "
                            f"current CTR leads performance."
                        ),
                    ),
                    RecommendationOut(
                        priority="high",
                        recommendation=(
                            f"Rewrite hooks and CTA on asset {worst.asset_id} "
                            f"for {worst.platform}; it is underperforming on CTR."
                        ),
                    ),
                    RecommendationOut(
                        priority="medium",
                        recommendation=(
                            f"Increase promotion density for coupon "
                            f"{settings.coupon_code} in the highest-converting "
                            f"formats."
                        ),
                    ),
                    RecommendationOut(
                        priority="medium",
                        recommendation=(
                            "Create a dedicated social landing page with one CTA, "
                            "challenge benefits, urgency, and testimonials."
                        ),
                    ),
                ]

            persisted: list[RecommendationOut] = []
            for rec in recs:
                session.add(
                    RecommendationDB(
                        priority=rec.priority,
                        recommendation=rec.recommendation,
                        active=True,
                    )
                )
                persisted.append(rec)

            session.commit()
            logger.info("Generated %d recommendations", len(persisted))
            return persisted
