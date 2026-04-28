from __future__ import annotations

import os
import platform
from typing import Tuple

from reportlab.pdfbase.pdfmetrics import registerFont
from reportlab.pdfbase.ttfonts import TTFont


def _exists(path: str) -> bool:
    return os.path.isfile(path)


def _search_font(candidates: list[Tuple[str, int]]) -> Tuple[str, int] | None:
    """Return the first (path, subfontIndex) that exists on disk."""
    for path, subfont in candidates:
        if _exists(path):
            return (path, subfont)
    return None


# -- macOS system font paths -------------------------------------------------

_MAC_BIZ_GOTHIC = (
    "/System/Library/AssetsV2/com_apple_MobileAsset_Font8/"
    "42529d87b12845309dd4a57dea9e58446826e94c.asset/AssetData/BIZ_UDGothic.ttc"
)
_MAC_BIZ_MINCHO = (
    "/System/Library/AssetsV2/com_apple_MobileAsset_Font8/"
    "0ebfdb7e5a2a1db668fa6209779e0725d6f6baba.asset/AssetData/BIZ_UDMincho-regular.ttf"
)
_MAC_STHEITI_MEDIUM = "/System/Library/Fonts/STHeiti Medium.ttc"
_MAC_STHEITI_LIGHT = "/System/Library/Fonts/STHeiti Light.ttc"


def _font_candidates(lang: str) -> Tuple[list[Tuple[str, int]], list[Tuple[str, int]]]:
    """Return (body_candidates, heading_candidates) for *lang*.

    Each candidate is (path, subfontIndex).  The first existing file wins.
    Environment variables take priority over platform defaults.
    """

    # --- env var overrides (highest priority) ---
    if lang == "zh-CN" and os.getenv("RISKLENS_FONT_ZH_CN"):
        p = os.getenv("RISKLENS_FONT_ZH_CN")
        return ([(p, 0)], [(p, 0)])
    if lang == "zh-TW" and os.getenv("RISKLENS_FONT_ZH_TW"):
        p = os.getenv("RISKLENS_FONT_ZH_TW")
        return ([(p, 0)], [(p, 0)])
    if lang == "ja":
        body_env = os.getenv("RISKLENS_FONT_JA_BODY")
        head_env = os.getenv("RISKLENS_FONT_JA_HEADING")
        if body_env or head_env:
            return (
                [(body_env, 0)] if body_env else [],
                [(head_env, 0)] if head_env else [],
            )

    sysname = platform.system()

    # --- macOS ---
    if sysname == "Darwin":
        if lang == "zh-CN":
            # Heiti SC Medium (subfont 1 of STHeiti Medium.ttc)
            body = [(_MAC_STHEITI_MEDIUM, 1)]
            head = [(_MAC_STHEITI_MEDIUM, 1)]
            return (body, head)
        elif lang == "zh-TW":
            # Heiti TC Medium (subfont 0 of STHeiti Medium.ttc)
            body = [(_MAC_STHEITI_MEDIUM, 0)]
            head = [(_MAC_STHEITI_MEDIUM, 0)]
            return (body, head)
        elif lang == "ja":
            body = [
                (_MAC_BIZ_GOTHIC, 0),
                (_MAC_STHEITI_MEDIUM, 1),  # last-resort fallback
            ]
            head = [
                (_MAC_BIZ_MINCHO, 0),
                (_MAC_BIZ_GOTHIC, 0),
            ]
            return (body, head)

    # --- Linux ---
    if sysname == "Linux":
        noto_regular = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
        noto_bold = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
        wqy = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
        droid = "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"

        body_candidates = [
            (noto_regular, 0),
            (wqy, 0),
            (droid, 0),
        ]
        head_candidates = [
            (noto_bold, 0),
            (noto_regular, 0),
        ]
        return (body_candidates, head_candidates)

    # --- Windows ---
    if sysname == "Windows":
        windir = os.environ.get("WINDIR", r"C:\Windows")
        fonts_dir = os.path.join(windir, "Fonts")

        if lang == "zh-CN":
            path = os.path.join(fonts_dir, "simsun.ttc")
            return ([(path, 0)], [(path, 0)])
        elif lang == "zh-TW":
            path = os.path.join(fonts_dir, "mingliu.ttc")
            return ([(path, 0)], [(path, 0)])
        elif lang == "ja":
            body = [(os.path.join(fonts_dir, "msgothic.ttc"), 0)]
            head = [(os.path.join(fonts_dir, "msmincho.ttc"), 0)]
            return (body, head)

    # Unknown platform — raise with guidance
    raise RuntimeError(
        f"Unsupported platform '{sysname}' for CJK PDF font discovery. "
        "Set RISKLENS_FONT_ZH_CN / RISKLENS_FONT_ZH_TW / "
        "RISKLENS_FONT_JA_BODY / RISKLENS_FONT_JA_HEADING "
        "environment variables to point to TrueType (.ttf/.ttc) font files."
    )


def _register_font(path: str, subfont: int, prefix: str) -> str:
    """Register a TTFont and return its ReportLab font name."""
    font_name = f"{prefix}_{subfont}"
    registerFont(TTFont(font_name, path, subfontIndex=subfont))
    return font_name


def register_cjk_fonts(lang: str) -> Tuple[str, str]:
    """Register CJK TrueType fonts for *lang* and return (body_font, heading_font).

    *lang* must be one of ``'zh-CN'``, ``'zh-TW'``, or ``'ja'``.
    """
    body_cands, head_cands = _font_candidates(lang)

    body_match = _search_font(body_cands)
    head_match = _search_font(head_cands)

    if body_match is None and head_match is None:
        _raise_not_found(lang, "body+heading", body_cands + head_cands)
    if body_match is None:
        body_match = head_match
    if head_match is None:
        head_match = body_match

    body_font = _register_font(body_match[0], body_match[1], f"CJK_{lang}_body")
    heading_font = _register_font(head_match[0], head_match[1], f"CJK_{lang}_head")

    return body_font, heading_font


def _raise_not_found(lang: str, role: str, candidates: list[Tuple[str, int]]) -> None:
    tried = "\n".join(f"  - {p}" for p, _ in candidates[:8])
    env_var = {
        "zh-CN": "RISKLENS_FONT_ZH_CN",
        "zh-TW": "RISKLENS_FONT_ZH_TW",
        "ja": "RISKLENS_FONT_JA_BODY / RISKLENS_FONT_JA_HEADING",
    }.get(lang, "RISKLENS_FONT_*")

    raise RuntimeError(
        f"No TrueType CJK font found for lang='{lang}' ({role}).\n"
        f"Tried:\n{tried}\n\n"
        f"Set the {env_var} environment variable to the path of a "
        f".ttf or .ttc font file that covers this language."
    )
