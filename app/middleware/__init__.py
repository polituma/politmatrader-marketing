"""
Security utilities: API key validation, webhook signature verification,
and request-ID middleware.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
import uuid
from collections import defaultdict
from typing import Optional

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import APIKeyHeader

from ..config import settings

logger = logging.getLogger("politma.security")

# ---------------------------------------------------------------------------
# API Key authentication
# ---------------------------------------------------------------------------
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(
    api_key: Optional[str] = Security(_api_key_header),
) -> str:
    """
    FastAPI dependency that enforces API key authentication.

    If no API keys are configured (dev mode), all requests pass through.
    In production, a valid key in the X-API-Key header is required.
    """
    if not settings.api_key_list:
        # No keys configured → open access (development mode)
        return "dev"
    if not api_key or api_key not in settings.api_key_list:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return api_key


# ---------------------------------------------------------------------------
# Webhook signature verification (inbound webhooks)
# ---------------------------------------------------------------------------
def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """
    Verify an inbound webhook payload using HMAC-SHA256.

    The caller should pass the raw request body and the value of the
    X-Webhook-Signature header.
    """
    if not settings.webhook_secret:
        logger.warning("Webhook secret not configured — skipping verification")
        return True

    expected = hmac.new(
        settings.webhook_secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


# ---------------------------------------------------------------------------
# Simple in-memory rate limiter
# ---------------------------------------------------------------------------
class RateLimiter:
    """
    Sliding-window rate limiter keyed by client IP.
    Good enough for a single-process deployment; swap for Redis-backed
    in a multi-instance setup.
    """

    def __init__(self, max_requests: int, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    def check(self, client_ip: str) -> bool:
        now = time.time()
        window_start = now - self.window
        hits = self._hits[client_ip]
        # Prune old entries
        self._hits[client_ip] = [t for t in hits if t > window_start]
        if len(self._hits[client_ip]) >= self.max_requests:
            return False
        self._hits[client_ip].append(now)
        return True


rate_limiter = RateLimiter(
    max_requests=settings.rate_limit_per_minute,
    window_seconds=60,
)
