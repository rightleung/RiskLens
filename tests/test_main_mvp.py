"""MVP endpoint regression tests for main.py."""

import asyncio
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

import main


client = TestClient(main.app)


def test_health_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json().get("status") == "healthy"


def test_root_ok_and_has_form():
    response = client.get("/")
    assert response.status_code == 200
    body = response.text
    assert 'id="assess-form"' in body
    assert "/static/js/app.js" in body


def test_assess_demo_success(monkeypatch):
    monkeypatch.setattr(
        main.service,
        "assess",
        lambda **kwargs: {
            "ticker": kwargs["ticker"],
            "assessment": {"z_score": 3.2, "risk_zone": "Safe (S)", "implied_rating": "A"},
            "key_metrics": {},
            "warnings": [],
        },
    )
    response = client.post("/api/assess", json={"ticker": "DEMO", "data_source": "demo"})
    assert response.status_code == 200
    data = response.json()
    assert data["assessment"]["risk_zone"] == "Safe (S)"


def test_assess_empty_ticker_validation():
    response = client.post("/api/assess", json={"ticker": "   ", "data_source": "demo"})
    assert response.status_code == 422


def test_assess_timeout_returns_504(monkeypatch):
    monkeypatch.setenv("ASSESS_TIMEOUT_SECONDS", "1")
    monkeypatch.setattr(main, "run_in_threadpool", AsyncMock(side_effect=asyncio.TimeoutError))

    response = client.post("/api/assess", json={"ticker": "DEMO", "data_source": "demo"})
    assert response.status_code == 504
    data = response.json()
    assert data.get("error_type") == "timeout"
    assert "评估超时" in data.get("error", "")
