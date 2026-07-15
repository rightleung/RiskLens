from __future__ import annotations

from pathlib import Path

import src.fonts as fonts


def test_bundled_cjk_fonts_are_selected_before_platform_paths(monkeypatch):
    monkeypatch.delenv("RISKLENS_FONT_ZH_CN", raising=False)
    monkeypatch.setattr(fonts.platform, "system", lambda: "Linux")

    body, heading = fonts._font_candidates("zh-CN")

    assert Path(body[0][0]).name == "NotoSansCJK-Regular.ttc"
    assert Path(heading[0][0]).name == "NotoSansCJK-Bold.ttc"


def test_font_environment_override_has_priority(monkeypatch, tmp_path):
    override = tmp_path / "custom.ttf"
    override.write_bytes(b"font")
    monkeypatch.setenv("RISKLENS_FONT_ZH_CN", str(override))

    body, heading = fonts._font_candidates("zh-CN")

    assert body == [(str(override), 0)]
    assert heading == [(str(override), 0)]
