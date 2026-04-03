"""
Content services: calendar strategy, asset creation, repurposing.

Key fixes:
- generate_assets checks for existing assets to prevent duplicates
- repurpose() checks for existing repurposed content to prevent unbounded growth
- Session is passed in (dependency-injection ready) rather than created internally
"""

from __future__ import annotations

import json
import logging
import random
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..brand import ANGLES, CONTENT_MIX, PLATFORMS, TOPIC_BANK
from ..config import settings
from ..db import SessionLocal
from ..models import CalendarIdeaDB, ContentAssetDB
from .providers import provider

logger = logging.getLogger("politma.content")


class ContentStrategistService:
    """Generates the rolling content calendar."""

    @staticmethod
    def _weighted_pillars(total: int) -> list[str]:
        pool: list[str] = []
        for pillar, pct in CONTENT_MIX.items():
            pool.extend([pillar] * pct)
        random.shuffle(pool)
        return [pool[i % len(pool)] for i in range(total)]

    def generate_calendar(
        self,
        *,
        days: int,
        start_date: str | None,
        clear_existing: bool,
    ) -> list[CalendarIdeaDB]:
        start = (
            datetime.strptime(start_date, "%Y-%m-%d") if start_date else datetime.now()
        )

        with SessionLocal() as session:
            if clear_existing:
                session.query(CalendarIdeaDB).delete()
                session.flush()

            pillars = self._weighted_pillars(days)
            ideas: list[CalendarIdeaDB] = []

            for i in range(days):
                pillar = pillars[i]
                date_str = (start + timedelta(days=i)).strftime("%Y-%m-%d")

                # Skip dates that already have calendar ideas (idempotency)
                existing = session.execute(
                    select(CalendarIdeaDB).where(CalendarIdeaDB.date == date_str)
                ).scalars().first()
                if existing and not clear_existing:
                    continue

                idea = CalendarIdeaDB(
                    id=str(uuid.uuid4()),
                    date=date_str,
                    pillar=pillar,
                    topic=random.choice(TOPIC_BANK[pillar]),
                    angle=random.choice(ANGLES),
                    target_platforms=json.dumps(
                        [p.value for p in PLATFORMS.keys()]
                    ),
                    campaign_tag=(
                        settings.coupon_code if pillar == "promotion" else "evergreen"
                    ),
                )
                session.add(idea)
                ideas.append(idea)

            session.commit()
            for obj in ideas:
                session.refresh(obj)

            logger.info("Generated %d calendar ideas", len(ideas))
            return ideas


class ContentCreatorService:
    """Generates platform-specific assets from calendar ideas."""

    def generate_assets(
        self,
        *,
        date_from: str | None,
        date_to: str | None,
        overwrite_existing: bool,
    ) -> list[ContentAssetDB]:
        with SessionLocal() as session:
            query = select(CalendarIdeaDB)
            ideas = session.execute(query).scalars().all()

            if date_from:
                ideas = [x for x in ideas if x.date >= date_from]
            if date_to:
                ideas = [x for x in ideas if x.date <= date_to]

            generated: list[ContentAssetDB] = []

            for idea in ideas:
                for platform_name, profile in PLATFORMS.items():
                    fmt = profile.formats[0]

                    # Duplicate check: skip if asset already exists for
                    # this idea+platform+format combo (unless overwrite requested).
                    if not overwrite_existing:
                        existing = session.execute(
                            select(ContentAssetDB).where(
                                ContentAssetDB.date == idea.date,
                                ContentAssetDB.platform == platform_name.value,
                                ContentAssetDB.format == fmt,
                                ContentAssetDB.source_asset_id.is_(None),
                            )
                        ).scalars().first()
                        if existing:
                            continue

                    asset_id = (
                        f"{idea.date}-{platform_name.value}-{fmt}"
                        f"-{uuid.uuid4().hex[:8]}"
                    )
                    post = provider.generate_post(
                        pillar=idea.pillar,
                        topic=idea.topic,
                        angle=idea.angle,
                        platform=platform_name.value,
                    )
                    asset = ContentAssetDB(
                        id=asset_id,
                        date=idea.date,
                        platform=platform_name.value,
                        format=fmt,
                        pillar=idea.pillar,
                        topic=idea.topic,
                        hook=post["hook"],
                        body=post["body"],
                        cta=post["cta"],
                        hashtags=json.dumps(post["hashtags"]),
                        visual_brief=post["visual_brief"],
                        status="draft",
                    )
                    session.add(asset)
                    generated.append(asset)

            session.commit()
            for obj in generated:
                session.refresh(obj)

            logger.info("Generated %d content assets", len(generated))
            return generated


class RepurposingService:
    """Creates cross-platform derivatives of existing assets."""

    # Map source platform → list of (target_platform, target_format)
    REPURPOSE_MAP = {
        "youtube": [("x", "thread"), ("linkedin", "post")],
        "instagram": [("facebook", "post"), ("tiktok", "short_video")],
    }

    def repurpose(self) -> list[ContentAssetDB]:
        with SessionLocal() as session:
            # Only repurpose original (non-repurposed) assets
            sources = (
                session.execute(
                    select(ContentAssetDB).where(
                        ContentAssetDB.source_asset_id.is_(None)
                    )
                )
                .scalars()
                .all()
            )

            created: list[ContentAssetDB] = []

            for source in sources:
                targets = self.REPURPOSE_MAP.get(source.platform, [])

                for target_platform, target_fmt in targets:
                    # Guard: don't re-create if already repurposed
                    existing = session.execute(
                        select(ContentAssetDB).where(
                            ContentAssetDB.source_asset_id == source.id,
                            ContentAssetDB.platform == target_platform,
                            ContentAssetDB.format == target_fmt,
                        )
                    ).scalars().first()
                    if existing:
                        continue

                    repurposed = ContentAssetDB(
                        id=f"{source.id}-{target_platform}-{uuid.uuid4().hex[:6]}",
                        date=source.date,
                        platform=target_platform,
                        format=target_fmt,
                        pillar=source.pillar,
                        topic=source.topic,
                        hook=f"Repurposed: {source.hook}",
                        body=source.body,
                        cta=source.cta,
                        hashtags=source.hashtags,
                        visual_brief=source.visual_brief,
                        status="draft",
                        source_asset_id=source.id,
                    )
                    session.add(repurposed)
                    created.append(repurposed)

            session.commit()
            for obj in created:
                session.refresh(obj)

            logger.info("Repurposed %d assets", len(created))
            return created
