"""
Brand constants: platforms, content mix, topic bank, creative angles.

This module is pure data — no database access, no side effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Platform definitions
# ---------------------------------------------------------------------------
class PlatformName(str, Enum):
    instagram = "instagram"
    tiktok = "tiktok"
    youtube = "youtube"
    x = "x"
    facebook = "facebook"
    linkedin = "linkedin"


@dataclass(frozen=True)
class PlatformProfile:
    name: PlatformName
    formats: List[str]
    default_post_times: List[str]
    character_limit: Optional[int] = None


PLATFORMS: Dict[PlatformName, PlatformProfile] = {
    PlatformName.instagram: PlatformProfile(
        PlatformName.instagram, ["reel", "carousel", "story"], ["13:00:00", "18:30:00"]
    ),
    PlatformName.tiktok: PlatformProfile(
        PlatformName.tiktok, ["short_video"], ["12:30:00", "19:30:00"]
    ),
    PlatformName.youtube: PlatformProfile(
        PlatformName.youtube, ["short", "community_post", "long_form"], ["17:00:00"]
    ),
    PlatformName.x: PlatformProfile(
        PlatformName.x, ["post", "thread"], ["09:00:00", "13:00:00", "17:00:00"], 280
    ),
    PlatformName.facebook: PlatformProfile(
        PlatformName.facebook, ["post", "story"], ["12:00:00"]
    ),
    PlatformName.linkedin: PlatformProfile(
        PlatformName.linkedin, ["post", "article"], ["08:30:00"]
    ),
}


# ---------------------------------------------------------------------------
# Content pillars (percentages must sum to 100)
# ---------------------------------------------------------------------------
CONTENT_MIX: Dict[str, int] = {
    "education": 40,
    "authority": 30,
    "promotion": 20,
    "lifestyle": 10,
}

# ---------------------------------------------------------------------------
# Topic bank per pillar
# ---------------------------------------------------------------------------
TOPIC_BANK: Dict[str, List[str]] = {
    "education": [
        "Why most traders fail funded challenges",
        "How discipline beats overtrading",
        "Risk management before profit targets",
        "The difference between retail emotion and professional execution",
        "How to prepare for a challenge account",
    ],
    "authority": [
        "What serious traders do before market open",
        "How elite traders protect capital",
        "The structure behind challenge consistency",
        "Why process matters more than hype",
        "How POLITMATRADER builds disciplined traders",
    ],
    "promotion": [
        "April Easter campaign",
        "Challenge discount announcement",
        "Why now is the best month to start a challenge",
        "Coupon-driven conversion push",
        "Limited-time funded journey promotion",
    ],
    "lifestyle": [
        "Disciplined trader mindset",
        "Morning routine of a serious trader",
        "What funded trading freedom can look like",
        "Trading with structure, not emotion",
        "The identity of a funded trader",
    ],
}

# ---------------------------------------------------------------------------
# Creative angles
# ---------------------------------------------------------------------------
ANGLES: List[str] = [
    "myth-busting",
    "step-by-step",
    "mistake-to-avoid",
    "challenge-focused",
    "identity transformation",
    "urgency-driven",
    "results-oriented",
]
