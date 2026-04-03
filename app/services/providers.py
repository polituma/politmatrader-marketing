"""
AI content providers.

Chain of responsibility: WebhookAIProvider → FallbackRuleBasedProvider.

Fixes:
- Added structured logging for webhook calls
- Added retry-worthy error classification
- Webhook response validation is stricter
- Fallback provider is always available
"""

from __future__ import annotations

import logging
from typing import Any, Dict

import httpx

from ..config import settings
from .utils import normalize_text

logger = logging.getLogger("politma.providers")


class AIContentProvider:
    """Abstract base for content generation."""

    def generate_post(
        self, *, pillar: str, topic: str, angle: str, platform: str
    ) -> Dict[str, Any]:
        raise NotImplementedError


class FallbackRuleBasedProvider(AIContentProvider):
    """
    Deterministic, rule-based content generator.
    Always available — no external dependencies.
    """

    def generate_post(
        self, *, pillar: str, topic: str, angle: str, platform: str
    ) -> Dict[str, Any]:
        if pillar == "promotion":
            hook = f"April only: use {settings.coupon_code} for 20% OFF all challenges."
            body = (
                f"This month only, {settings.brand_name} is giving traders a reason to act. "
                f"Use code {settings.coupon_code} and save 20% across all challenges "
                f"at {settings.brand_domain}."
            )
            cta = (
                f"Use {settings.coupon_code} now \u2014 "
                f"{settings.cta_primary}: {settings.brand_domain}"
            )
        elif pillar == "education":
            hook = f"Most traders fail because they ignore this: {topic.lower()}."
            body = (
                f"{topic} separates impulsive traders from disciplined performers. "
                "The goal is repeatable execution, risk control, and challenge consistency."
            )
            cta = f"{settings.cta_primary} at {settings.brand_domain}"
        elif pillar == "authority":
            hook = f"Serious traders know this: {topic.lower()}."
            body = (
                f"At {settings.brand_name}, the focus is precision, structure, and "
                "capital protection. Traders who build process outperform traders "
                "who chase noise."
            )
            cta = f"Learn the standard. {settings.cta_primary}: {settings.brand_domain}"
        else:  # lifestyle
            hook = f"The funded trader identity starts here: {topic.lower()}."
            body = (
                "Trading freedom is built on discipline, patience, and structure. "
                "Stop glamorizing hype and start building execution habits that scale."
            )
            cta = f"Build the mindset. {settings.cta_primary}: {settings.brand_domain}"

        hashtags = [
            "#PolitmaTrader",
            "#FundedTrader",
            "#TradingChallenge",
            "#RiskManagement",
            "#TraderMindset",
        ]
        if pillar == "promotion":
            hashtags.extend([f"#{settings.coupon_code}", "#AprilPromo", "#EasterSale"])

        char_limit = 220 if platform == "x" else None

        return {
            "hook": normalize_text(hook, char_limit),
            "body": normalize_text(body),
            "cta": normalize_text(cta),
            "hashtags": hashtags[:8],
            "visual_brief": (
                f"Create a premium black-and-gold {platform} creative for "
                f"{settings.brand_name}. Topic: {topic}. Angle: {angle}. "
                f"Use bold typography and a strong CTA. "
                f"If promotional, highlight {settings.coupon_code} and the April discount."
            ),
        }


class WebhookAIProvider(AIContentProvider):
    """
    Calls an external AI webhook. Falls back to rule-based on any failure.
    """

    REQUIRED_FIELDS = {"hook", "body", "cta", "hashtags", "visual_brief"}

    def __init__(self, fallback: AIContentProvider):
        self.fallback = fallback

    def generate_post(
        self, *, pillar: str, topic: str, angle: str, platform: str
    ) -> Dict[str, Any]:
        if not settings.ai_webhook_url:
            return self.fallback.generate_post(
                pillar=pillar, topic=topic, angle=angle, platform=platform
            )

        payload = {
            "brand_name": settings.brand_name,
            "brand_domain": settings.brand_domain,
            "coupon_code": settings.coupon_code,
            "coupon_description": settings.coupon_description,
            "pillar": pillar,
            "topic": topic,
            "angle": angle,
            "platform": platform,
            "cta_primary": settings.cta_primary,
        }
        headers = {"Content-Type": "application/json"}
        if settings.ai_webhook_token:
            headers["Authorization"] = f"Bearer {settings.ai_webhook_token}"

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    settings.ai_webhook_url, json=payload, headers=headers
                )
                response.raise_for_status()
                data = response.json()

                missing = self.REQUIRED_FIELDS - set(data.keys())
                if missing:
                    logger.warning(
                        "AI webhook response missing fields %s — falling back",
                        missing,
                    )
                    raise ValueError(f"Missing fields: {missing}")

                logger.info(
                    "AI webhook generated content for %s/%s/%s",
                    platform,
                    pillar,
                    angle,
                )
                return data

        except httpx.TimeoutException:
            logger.warning("AI webhook timed out for %s/%s", platform, pillar)
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "AI webhook returned %s for %s/%s",
                exc.response.status_code,
                platform,
                pillar,
            )
        except Exception as exc:
            logger.warning("AI webhook error: %s — falling back", exc)

        return self.fallback.generate_post(
            pillar=pillar, topic=topic, angle=angle, platform=platform
        )


# Module-level singleton
provider = WebhookAIProvider(FallbackRuleBasedProvider())
