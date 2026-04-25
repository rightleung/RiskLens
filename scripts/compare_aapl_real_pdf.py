#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import src.reportlab_pdf_exporter as reportlab_pdf_exporter

DEFAULT_REFERENCE = Path("/Users/rightleung/Downloads/AAPL_Real_Report.pdf")
DEFAULT_FIXTURE = ROOT / "tests" / "fixtures" / "aapl_real_report.json"
DEFAULT_PAGES = (1, 4, 6, 7, 10)
_GENERATED_AT_RE = re.compile(r"(Generated At:\s+)[0-9]{4}-[0-9]{2}-[0-9]{2}\s+[0-9]{2}:[0-9]{2}\s+UTC")


def _collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _normalize_dynamic_text(text: str) -> str:
    return _GENERATED_AT_RE.sub(r"\1<timestamp>", text)


def _apply_replacements(value: object, replacements: list[tuple[str, str]]) -> object:
    if isinstance(value, str):
        text = value
        for old, new in replacements:
            text = text.replace(old, new)
        return text
    if isinstance(value, list):
        return [_apply_replacements(item, replacements) for item in value]
    if isinstance(value, tuple):
        return tuple(_apply_replacements(item, replacements) for item in value)
    if isinstance(value, dict):
        return {key: _apply_replacements(item, replacements) for key, item in value.items()}
    return value


def _parse_replacements(items: list[str]) -> list[tuple[str, str]]:
    parsed: list[tuple[str, str]] = []
    for item in items:
        if "=" not in item:
            raise ValueError(f"Replacement must use OLD=NEW syntax: {item!r}")
        old, new = item.split("=", 1)
        if not old:
            raise ValueError(f"Replacement source must not be empty: {item!r}")
        parsed.append((old, new))
    return parsed


def _read_report(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _extract_pages(pdf_path: Path) -> list[str]:
    if not shutil.which("pdftotext"):
        raise RuntimeError("pdftotext is required for page-level text comparison.")
    extracted = subprocess.check_output(["pdftotext", "-layout", str(pdf_path), "-"], text=True)
    pages = extracted.split("\f")
    if pages and not pages[-1].strip():
        pages = pages[:-1]
    return pages


def _render_page_png(pdf_path: Path, page: int, workdir: Path) -> Path:
    if not shutil.which("pdftocairo"):
        raise RuntimeError("pdftocairo is required for page image comparison.")
    workdir.mkdir(parents=True, exist_ok=True)
    prefix = workdir / f"page_{page}"
    subprocess.run(
        ["pdftocairo", "-png", "-f", str(page), "-l", str(page), str(pdf_path), str(prefix)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    matches = sorted(prefix.parent.glob(f"{prefix.name}-*.png"))
    if not matches:
        raise RuntimeError(f"Failed to render page {page} from {pdf_path}.")
    return matches[0]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_pdf_bytes(data: bytes, workdir: Path, name: str) -> Path:
    pdf_path = workdir / name
    pdf_path.write_bytes(data)
    return pdf_path


def _page_diff(reference: str, generated: str, page: int) -> str | None:
    ref_lines = [_normalize_dynamic_text(line).rstrip() for line in reference.splitlines()]
    gen_lines = [_normalize_dynamic_text(line).rstrip() for line in generated.splitlines()]
    if ref_lines == gen_lines:
        return None
    diff = difflib.unified_diff(
        ref_lines,
        gen_lines,
        fromfile=f"reference page {page}",
        tofile=f"generated page {page}",
        lineterm="",
    )
    return "\n".join(diff)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare the current AAPL PDF generator against a reference PDF.")
    parser.add_argument("--reference", type=Path, default=DEFAULT_REFERENCE, help="Reference PDF to compare against.")
    parser.add_argument(
        "--fixture",
        type=Path,
        default=DEFAULT_FIXTURE,
        help="Report JSON fixture used to generate the current PDF.",
    )
    parser.add_argument(
        "--pages",
        type=int,
        nargs="+",
        default=list(DEFAULT_PAGES),
        help="1-based page numbers to inspect.",
    )
    parser.add_argument(
        "--replace",
        action="append",
        default=[],
        help="Recursively replace OLD=NEW in the report JSON before generating the comparison PDF. Can be repeated.",
    )
    args = parser.parse_args()

    if not args.reference.exists():
        print(f"Reference PDF not found: {args.reference}", file=sys.stderr)
        return 2
    if not args.fixture.exists():
        print(f"Fixture JSON not found: {args.fixture}", file=sys.stderr)
        return 2

    report = _read_report(args.fixture)
    replacements = _parse_replacements(args.replace)
    if replacements:
        report = _apply_replacements(copy.deepcopy(report), replacements)
        print("Applied replacements:")
        for old, new in replacements:
            print(f"  {old!r} -> {new!r}")
    generated_bytes = reportlab_pdf_exporter.generate_full_pdf(report, lang="en", theme="dark")

    with tempfile.TemporaryDirectory(prefix="aapl_pdf_compare_") as tmp:
        workdir = Path(tmp)
        generated_pdf = _write_pdf_bytes(generated_bytes, workdir, "generated.pdf")
        reference_pdf = args.reference
        print(f"Reference SHA256: {_sha256(reference_pdf)}")
        print(f"Generated SHA256: {_sha256(generated_pdf)}")

        ref_pages = _extract_pages(reference_pdf)
        gen_pages = _extract_pages(generated_pdf)
        selected_pages = [page for page in args.pages if page >= 1]

        print(f"Reference:  {reference_pdf}")
        print(f"Generated:  {generated_pdf}")
        print(f"Pages:      {len(ref_pages)} vs {len(gen_pages)}")
        print("")

        any_diff = False
        can_compare_images = shutil.which("pdftocairo") is not None
        for page in selected_pages:
            ref_text = ref_pages[page - 1] if page - 1 < len(ref_pages) else ""
            gen_text = gen_pages[page - 1] if page - 1 < len(gen_pages) else ""
            text_diff = _page_diff(ref_text, gen_text, page)

            image_status = "skipped"
            if page != 1 and can_compare_images and page - 1 < len(ref_pages) and page - 1 < len(gen_pages):
                ref_png = _render_page_png(reference_pdf, page, workdir / "reference")
                gen_png = _render_page_png(generated_pdf, page, workdir / "generated")
                image_status = "same" if _sha256(ref_png) == _sha256(gen_png) else "different"
            elif page == 1 and can_compare_images:
                image_status = "ignored (timestamp)"

            print(f"Page {page}: text={'same' if text_diff is None else 'different'}, image={image_status}")
            if text_diff is not None:
                any_diff = True
                print(text_diff)
                print("")
            if image_status == "different":
                any_diff = True

        gen_text = "\n".join(gen_pages)
        for _old, new in replacements:
            if new not in gen_text:
                print(f"Canary check: replacement target {new!r} not found in generated text.")
                any_diff = True
            else:
                print(f"Canary check: replacement target {new!r} found in generated text.")

        if not can_compare_images:
            print("Image comparison skipped: pdftocairo not available.")

        return 1 if any_diff else 0


if __name__ == "__main__":
    raise SystemExit(main())
