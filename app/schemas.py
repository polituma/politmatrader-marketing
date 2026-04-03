"""
Pydantic request/response schemas.

Changes:
- Added date format validation with regex
- Added pagination support
- Added webhook payload schemas for documentation
- Tightened field constraints
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _validate_date_str(v: Optional[str]) -> Optional[str]:
    if v is not None and not _DATE_RE.match(v):
        raise ValueError("Date must be in YYYY-MM-DD format")
    return v


# ---------------------------------------------------------------------------
# Generic
# ---------------------------------------------------------------------------
class MessageOut(BaseModel):
    ok: bool
    detail: Any


class BootstrapResponse(BaseModel):
    ok: bool
    message: str
    version: str = "1.0.0"


class HealthResponse(BaseModel):
    status: str
    environment: str
    database: str
    scheduler: str


# ---------------------------------------------------------------------------
# Content Calendar
# ---------------------------------------------------------------------------
class GenerateCalendarRequest(BaseModel):
    days: int = Field(default=30, ge=1, le=90)
    start_date: Optional[str] = None
    clear_existing: bool = False

    @field_validator("start_date")
    @classmethod
    def check_start_date(cls, v):
        return _validate_date_str(v)


class CalendarIdeaOut(BaseModel):
    id: str
    date: str
    pillar: str
    topic: str
    angle: str
    target_platforms: List[str]
    campaign_tag: str


# ---------------------------------------------------------------------------
# Content Assets
# ---------------------------------------------------------------------------
class GenerateAssetsRequest(BaseModel):
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    overwrite_existing: bool = False

    @field_validator("date_from", "date_to")
    @classmethod
    def check_dates(cls, v):
        return _validate_date_str(v)


class AssetOut(BaseModel):
    id: str
    date: str
    platform: str
    format: str
    pillar: str
    topic: str
    hook: str
    body: str
    cta: str
    hashtags: List[str]
    visual_brief: str
    status: str
    source_asset_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Distribution
# ---------------------------------------------------------------------------
class QueueRequest(BaseModel):
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    only_status: str = "draft"

    @field_validator("date_from", "date_to")
    @classmethod
    def check_dates(cls, v):
        return _validate_date_str(v)


class PublishRequest(BaseModel):
    limit: int = Field(default=50, ge=1, le=500)


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------
class PerformanceIngestRequest(BaseModel):
    asset_id: str = Field(..., min_length=1)
    platform: str = Field(..., min_length=1)
    impressions: int = Field(ge=0)
    clicks: int = Field(ge=0)
    engagements: int = Field(ge=0)
    conversions: int = Field(ge=0)
    spend: float = Field(default=0.0, ge=0.0)


class SummaryOut(BaseModel):
    total_assets: int
    total_impressions: int
    total_clicks: int
    total_engagements: int
    total_conversions: int
    avg_ctr: float
    avg_engagement_rate: float
    avg_conversion_rate: float


class RecommendationOut(BaseModel):
    priority: str
    recommendation: str


# ---------------------------------------------------------------------------
# Webhook Payload Contracts (documentation models)
# ---------------------------------------------------------------------------
class AIWebhookRequest(BaseModel):
    """Payload sent TO your AI content generation endpoint."""
    brand_name: str
    brand_domain: str
    coupon_code: str
    pillar: str
    topic: str
    angle: str
    platform: str


class AIWebhookResponse(BaseModel):
    """Expected response FROM your AI content generation endpoint."""
    hook: str
    body: str
    cta: str
    hashtags: List[str]
    visual_brief: str


class PublishWebhookRequest(BaseModel):
    """Payload sent TO your social publishing endpoint."""
    asset_id: str
    platform: str
    format: str
    hook: str
    body: str
    cta: str
    hashtags: str  # JSON array string
    visual_brief: str
    scheduled_time: str


class PublishWebhookResponse(BaseModel):
    """Expected response FROM your social publishing endpoint."""
    external_post_id: str
    status: str = "published"
    message: Optional[str] = None
