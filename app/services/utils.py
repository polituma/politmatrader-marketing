"""Shared utility functions."""

from __future__ import annotations

import json
import re
import uuid


def safe_json_loads(value: str, fallback=None):
    """Parse JSON string, returning *fallback* on any error."""
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return fallback


def normalize_text(value: str, max_len: int | None = None) -> str:
    """Collapse whitespace and optionally truncate with an ellipsis."""
    value = re.sub(r"\s+", " ", value).strip()
    if max_len and len(value) > max_len:
        return value[: max_len - 1].rstrip() + "\u2026"
    return value


def new_id(prefix: str = "") -> str:
    """Short unique identifier, optionally prefixed."""
    body = uuid.uuid4().hex[:10]
    return f"{prefix}{body}" if prefix else body
