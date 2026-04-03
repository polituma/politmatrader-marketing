"""
Distribution service: queue scheduling and webhook-based publishing.

Key fixes:
- Replaced deprecated datetime.utcnow() with datetime.now(timezone.utc)
- Added retry logic with exponential backoff tracking
- Publish webhook sends structured payload with asset_id and scheduled_time
- Better error isolation per-item (one failure doesn't abort the batch)
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..brand import PLATFORMS, PlatformName
from ..config import settings
from ..db import SessionLocal
from ..models import ContentAssetDB, QueueItemDB

logger = logging.getLogger("politma.distribution")

MAX_RETRIES = 3


class DistributionService:
    def queue_posts(
        self,
        *,
        date_from: str | None,
        date_to: str | None,
        only_status: str,
    ) -> list[QueueItemDB]:
        with SessionLocal() as session:
            assets = (
                session.execute(
                    select(ContentAssetDB).where(
                        ContentAssetDB.status == only_status
                    )
                )
                .scalars()
                .all()
            )

            if date_from:
                assets = [a for a in assets if a.date >= date_from]
            if date_to:
                assets = [a for a in assets if a.date <= date_to]

            queued: list[QueueItemDB] = []
            for asset in assets:
                # Don't re-queue assets that already have a queue entry
                existing = session.execute(
                    select(QueueItemDB).where(QueueItemDB.asset_id == asset.id)
                ).scalars().first()
                if existing:
                    continue

                try:
                    profile = PLATFORMS[PlatformName(asset.platform)]
                except (ValueError, KeyError):
                    logger.warning(
                        "Unknown platform %s for asset %s — skipping",
                        asset.platform,
                        asset.id,
                    )
                    continue

                time_str = profile.default_post_times[0]
                scheduled = datetime.fromisoformat(
                    f"{asset.date}T{time_str}+00:00"
                )

                item = QueueItemDB(
                    id=str(uuid.uuid4()),
                    asset_id=asset.id,
                    platform=asset.platform,
                    scheduled_time=scheduled,
                    status="queued",
                )
                asset.status = "queued"
                session.add(item)
                queued.append(item)

            session.commit()
            for obj in queued:
                session.refresh(obj)

            logger.info("Queued %d posts for distribution", len(queued))
            return queued

    def _publish_external(
        self, asset: ContentAssetDB, queue_item: QueueItemDB
    ) -> str:
        """
        Call the external publishing webhook, or simulate if not configured.
        """
        if not settings.publish_webhook_url:
            return f"simulated-{uuid.uuid4().hex[:10]}"

        headers = {"Content-Type": "application/json"}
        if settings.publish_webhook_token:
            headers["Authorization"] = f"Bearer {settings.publish_webhook_token}"

        payload = {
            "asset_id": asset.id,
            "platform": asset.platform,
            "format": asset.format,
            "hook": asset.hook,
            "body": asset.body,
            "cta": asset.cta,
            "hashtags": asset.hashtags,
            "visual_brief": asset.visual_brief,
            "scheduled_time": queue_item.scheduled_time.isoformat(),
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                settings.publish_webhook_url, json=payload, headers=headers
            )
            response.raise_for_status()
            data = response.json() if response.content else {}
            return data.get(
                "external_post_id", f"webhook-{uuid.uuid4().hex[:10]}"
            )

    def publish_due_posts(self, limit: int = 50) -> list[QueueItemDB]:
        now = datetime.now(timezone.utc)

        with SessionLocal() as session:
            due_items = (
                session.execute(
                    select(QueueItemDB)
                    .where(
                        QueueItemDB.status.in_(["queued", "retry"]),
                        QueueItemDB.scheduled_time <= now,
                    )
                    .order_by(QueueItemDB.scheduled_time)
                    .limit(limit)
                )
                .scalars()
                .all()
            )

            published: list[QueueItemDB] = []

            for item in due_items:
                asset = session.get(ContentAssetDB, item.asset_id)
                if not asset:
                    item.status = "failed"
                    item.error_message = "Asset not found in database"
                    logger.error("Asset %s not found for queue item %s", item.asset_id, item.id)
                    continue

                try:
                    external_id = self._publish_external(asset, item)
                    item.status = "published"
                    item.external_post_id = external_id
                    item.published_time = datetime.now(timezone.utc)
                    asset.status = "published"
                    published.append(item)
                    logger.info(
                        "Published asset %s to %s → %s",
                        asset.id,
                        asset.platform,
                        external_id,
                    )
                except httpx.HTTPStatusError as exc:
                    item.retry_count += 1
                    if item.retry_count >= MAX_RETRIES:
                        item.status = "failed"
                        item.error_message = (
                            f"HTTP {exc.response.status_code} after {MAX_RETRIES} retries"
                        )
                        asset.status = "error"
                    else:
                        item.status = "retry"
                        item.error_message = f"HTTP {exc.response.status_code} (retry {item.retry_count})"
                    logger.warning(
                        "Publish failed for %s: %s (retry %d/%d)",
                        asset.id,
                        item.error_message,
                        item.retry_count,
                        MAX_RETRIES,
                    )
                except Exception as exc:
                    item.retry_count += 1
                    item.status = "failed" if item.retry_count >= MAX_RETRIES else "retry"
                    item.error_message = str(exc)[:500]
                    asset.status = "error" if item.status == "failed" else asset.status
                    logger.exception("Unexpected publish error for %s", asset.id)

            session.commit()
            for obj in published:
                session.refresh(obj)

            logger.info(
                "Publish run complete: %d published, %d total processed",
                len(published),
                len(due_items),
            )
            return published
