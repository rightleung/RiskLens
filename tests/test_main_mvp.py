"""MVP endpoint regression tests for main.py."""

import os
import sys
import time

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

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

    def _slow_assess(**_kwargs):
        time.sleep(1.2)
        return {"ok": True}

    monkeypatch.setattr(main.service, "assess", _slow_assess)

    response = client.post("/api/assess", json={"ticker": "DEMO", "data_source": "demo"})
    assert response.status_code == 504
    detail = response.json().get("detail", {})
    assert "评估超时" in detail.get("error", "")
