"""
Test suite for POLITMATRADER Marketing System.

Uses an in-memory SQLite database for isolation.
Run with: pytest tests/ -v
"""

from __future__ import annotations

import json
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Force test database before importing app
os.environ["DATABASE_URL"] = "sqlite:///./test_politma.db"
os.environ["APP_ENV"] = "test"
os.environ["API_KEYS"] = ""  # open access for tests

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def reset_db():
    """Recreate all tables before each test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


# ── Root & Health ──────────────────────────────────────────────────────────

class TestSystem:
    def test_root(self, client):
        r = client.get("/")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "POLITMATRADER" in data["app"]

    def test_health(self, client):
        r = client.get("/system/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"

    def test_bootstrap(self, client):
        r = client.post("/system/bootstrap")
        assert r.status_code == 200
        assert r.json()["ok"] is True


# ── Content Calendar ──────────────────────────────────────────────────────

class TestContentCalendar:
    def test_generate_calendar_default(self, client):
        r = client.post("/content/generate-calendar", json={"days": 5})
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 5
        assert all("id" in item for item in data)

    def test_generate_calendar_with_start_date(self, client):
        r = client.post(
            "/content/generate-calendar",
            json={"days": 3, "start_date": "2025-04-01"},
        )
        assert r.status_code == 200
        dates = [item["date"] for item in r.json()]
        assert dates == ["2025-04-01", "2025-04-02", "2025-04-03"]

    def test_generate_calendar_idempotent(self, client):
        """Calling twice without clear_existing should not create duplicates."""
        client.post(
            "/content/generate-calendar",
            json={"days": 3, "start_date": "2025-06-01"},
        )
        r2 = client.post(
            "/content/generate-calendar",
            json={"days": 3, "start_date": "2025-06-01"},
        )
        assert r2.status_code == 200
        assert len(r2.json()) == 0  # no new items

    def test_invalid_date_format(self, client):
        r = client.post(
            "/content/generate-calendar",
            json={"days": 3, "start_date": "04/01/2025"},
        )
        assert r.status_code == 422


# ── Content Assets ────────────────────────────────────────────────────────

class TestContentAssets:
    def test_generate_assets(self, client):
        client.post(
            "/content/generate-calendar",
            json={"days": 1, "start_date": "2025-05-01"},
        )
        r = client.post("/content/generate-assets", json={})
        assert r.status_code == 200
        assets = r.json()
        assert len(assets) > 0
        # Should have assets for multiple platforms
        platforms = set(a["platform"] for a in assets)
        assert len(platforms) > 1

    def test_assets_have_required_fields(self, client):
        client.post(
            "/content/generate-calendar",
            json={"days": 1, "start_date": "2025-05-01"},
        )
        r = client.post("/content/generate-assets", json={})
        for asset in r.json():
            assert asset["hook"]
            assert asset["body"]
            assert asset["cta"]
            assert isinstance(asset["hashtags"], list)
            assert asset["status"] in ("draft",)


# ── Distribution ──────────────────────────────────────────────────────────

class TestDistribution:
    def _setup_assets(self, client):
        client.post(
            "/content/generate-calendar",
            json={"days": 1, "start_date": "2025-05-01"},
        )
        client.post("/content/generate-assets", json={})

    def test_queue(self, client):
        self._setup_assets(client)
        r = client.post("/distribution/queue", json={"only_status": "draft"})
        assert r.status_code == 200
        assert r.json()["detail"]["queued"] > 0

    def test_publish(self, client):
        self._setup_assets(client)
        client.post("/distribution/queue", json={"only_status": "draft"})
        r = client.post("/distribution/publish", json={"limit": 100})
        assert r.status_code == 200
        # Published count depends on scheduled_time vs now — may be 0 for future dates
        assert "published" in r.json()["detail"]


# ── Analytics ─────────────────────────────────────────────────────────────

class TestAnalytics:
    def test_summary_empty(self, client):
        r = client.get("/analytics/summary")
        assert r.status_code == 200
        data = r.json()
        assert data["total_assets"] == 0
        assert data["avg_ctr"] == 0.0

    def test_ingest_missing_asset(self, client):
        r = client.post(
            "/analytics/ingest",
            json={
                "asset_id": "nonexistent",
                "platform": "x",
                "impressions": 100,
                "clicks": 5,
                "engagements": 10,
                "conversions": 1,
            },
        )
        assert r.status_code == 404


# ── Optimizer ─────────────────────────────────────────────────────────────

class TestOptimizer:
    def test_recommendations_empty(self, client):
        r = client.get("/optimizer/recommendations")
        assert r.status_code == 200
        recs = r.json()
        assert len(recs) >= 1
        assert all("priority" in rec for rec in recs)


# ── Full Pipeline ─────────────────────────────────────────────────────────

class TestFullPipeline:
    def test_daily_run(self, client):
        r = client.post("/system/daily-run")
        assert r.status_code == 200
        detail = r.json()["detail"]
        assert detail["calendar_items"] > 0
        assert detail["created_assets"] > 0
