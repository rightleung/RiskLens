"""Tests for the rich assessment service demo payload."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from services import RichAssessmentService


def test_demo_payload_contains_multiple_periods():
    payload = RichAssessmentService._build_demo_data("DEMO")
    history = payload["history"]

    assert len(history) >= 5
    assert history[0]["is_quarterly"] is True
    assert [entry["year_label"] for entry in history[:5]] == ["25Q3", "24Q3", "FY24", "FY23", "FY22"]
    assert history[1]["income"].shape[0] >= 10
    assert history[1]["balance"].shape[0] >= 10
    assert history[1]["cash"].shape[0] >= 10
