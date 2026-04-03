"""
SQLAlchemy ORM models.

Fixes over original:
- utcnow() no longer strips timezone then stores naive — we store UTC-aware
  datetimes and let SQLAlchemy handle it.  For SQLite compatibility the
  column type stays DateTime (SQLite stores text anyway), but the Python
  objects are always tz-aware.
- updated_at uses onupdate so it auto-refreshes on row changes.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def _utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Calendar Ideas
# ---------------------------------------------------------------------------
class CalendarIdeaDB(Base):
    __tablename__ = "calendar_ideas"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    date: Mapped[str] = mapped_column(String(10), index=True)
    pillar: Mapped[str] = mapped_column(String(32), index=True)
    topic: Mapped[str] = mapped_column(String(255))
    angle: Mapped[str] = mapped_column(String(64))
    target_platforms: Mapped[str] = mapped_column(Text)
    campaign_tag: Mapped[str] = mapped_column(String(64), default="evergreen")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


# ---------------------------------------------------------------------------
# Content Assets
# ---------------------------------------------------------------------------
class ContentAssetDB(Base):
    __tablename__ = "content_assets"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    date: Mapped[str] = mapped_column(String(10), index=True)
    platform: Mapped[str] = mapped_column(String(32), index=True)
    format: Mapped[str] = mapped_column(String(32))
    pillar: Mapped[str] = mapped_column(String(32), index=True)
    topic: Mapped[str] = mapped_column(String(255))
    hook: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    cta: Mapped[str] = mapped_column(Text)
    hashtags: Mapped[str] = mapped_column(Text)  # JSON array
    visual_brief: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    source_asset_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


# ---------------------------------------------------------------------------
# Distribution Queue
# ---------------------------------------------------------------------------
class QueueItemDB(Base):
    __tablename__ = "distribution_queue"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    asset_id: Mapped[str] = mapped_column(String(64), index=True)
    platform: Mapped[str] = mapped_column(String(32), index=True)
    scheduled_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    published_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    external_post_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


# ---------------------------------------------------------------------------
# Performance Records
# ---------------------------------------------------------------------------
class PerformanceRecordDB(Base):
    __tablename__ = "performance_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[str] = mapped_column(String(64), index=True)
    platform: Mapped[str] = mapped_column(String(32), index=True)
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    engagements: Mapped[int] = mapped_column(Integer, default=0)
    conversions: Mapped[int] = mapped_column(Integer, default=0)
    spend: Mapped[float] = mapped_column(Float, default=0.0)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------
class RecommendationDB(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    priority: Mapped[str] = mapped_column(String(16), index=True)
    recommendation: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
