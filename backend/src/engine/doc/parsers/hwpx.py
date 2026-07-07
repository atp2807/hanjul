"""HWPX parser — converts HWPX (open HWP successor) documents to UniversalDoc.

HWPX is a zip container (mimetype ``application/hwp+zip``) holding OWPML XML:
``Contents/header.xml`` plus one ``Contents/sectionN.xml`` per section.  This
parser walks the section XML with the stdlib (``zipfile`` + ``ElementTree``),
extracting paragraphs (``hp:p`` -> PARAGRAPH) and tables (``hp:tbl`` -> TABLE)
in a meta shape kept deliberately consistent with ``parsers/hwp.py`` so the
viewer/dialect can render either format identically.  Pure stdlib — no new deps.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
import zipfile
from io import BytesIO

from src.engine.doc.models import Block, BlockType, Page, UniversalDoc

# ---------------------------------------------------------------------------
# OWPML namespaces (measured from reference_data/hwpx/*.hwpx)
# ---------------------------------------------------------------------------
_NS_PARAGRAPH = "http://www.hancom.co.kr/hwpml/2011/paragraph"  # hp:
_NS_SECTION = "http://www.hancom.co.kr/hwpml/2011/section"       # hs:

_MIMETYPE = "application/hwp+zip"
_HWPUNIT_PER_INCH = 7200
_MM_PER_INCH = 25.4


def _hp(tag: str) -> str:
    """Return a Clark-notation qualified name in the hp: (paragraph) namespace."""
    return f"{{{_NS_PARAGRAPH}}}{tag}"


def _to_mm(value: int) -> float:
    """Convert an HWPUNIT length (1/7200 inch) to millimetres, matching hwp.py."""
    return round(value / _HWPUNIT_PER_INCH * _MM_PER_INCH, 1)


def _as_int(value: str | None, default: int = 0) -> int:
    """Parse an attribute string to int, tolerating missing/blank values."""
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def _text_excluding_tables(element: ET.Element) -> str:
    """Concatenate every ``hp:t`` text under *element*, skipping nested tables.

    HWPX text lives in ``hp:t`` leaves; a table's own text is collected
    separately, so nested ``hp:tbl`` subtrees are pruned to avoid pulling cell
    text into the surrounding paragraph or an enclosing cell.
    """
    parts: list[str] = []
    for child in element:
        if child.tag == _hp("tbl"):
            continue
        if child.tag == _hp("t"):
            parts.append("".join(child.itertext()))
        else:
            parts.append(_text_excluding_tables(child))
    return "".join(parts)


# ---------------------------------------------------------------------------
# Table parsing  (hp:tbl -> TABLE block, hwp.py-compatible meta)
# ---------------------------------------------------------------------------

def _parse_cell(tc: ET.Element) -> dict:
    """Extract one ``hp:tc`` cell into hwp.py's cell dict shape."""
    addr = tc.find(_hp("cellAddr"))
    span = tc.find(_hp("cellSpan"))
    size = tc.find(_hp("cellSz"))

    cell: dict = {
        "col": _as_int(addr.get("colAddr")) if addr is not None else 0,
        "row": _as_int(addr.get("rowAddr")) if addr is not None else 0,
        "colspan": _as_int(span.get("colSpan"), 1) if span is not None else 1,
        "rowspan": _as_int(span.get("rowSpan"), 1) if span is not None else 1,
    }
    if size is not None:
        cell["width_mm"] = _to_mm(_as_int(size.get("width")))
        cell["height_mm"] = _to_mm(_as_int(size.get("height")))
    cell["text"] = _text_excluding_tables(tc)
    return cell


def _build_grid(cells: list[dict], row_count: int, col_count: int) -> list[list[str]]:
    """Place cell texts into a ``row_count`` x ``col_count`` grid by address.

    Cells covered by a preceding cell's span keep their empty placeholder, so
    the grid stays rectangular and consistent with hwp.py's ``rows`` output.
    """
    rows_needed = max(row_count, 1 + max((c["row"] for c in cells), default=-1))
    cols_needed = max(col_count, 1 + max((c["col"] for c in cells), default=-1))
    grid: list[list[str]] = [["" for _ in range(cols_needed)] for _ in range(rows_needed)]
    for cell in cells:
        r, c = cell["row"], cell["col"]
        if 0 <= r < rows_needed and 0 <= c < cols_needed:
            grid[r][c] = cell["text"]
    return grid


def _parse_table(tbl: ET.Element) -> Block:
    """Convert an ``hp:tbl`` element into a TABLE Block (hwp.py meta shape)."""
    col_count = _as_int(tbl.get("colCnt"))
    row_count = _as_int(tbl.get("rowCnt"))

    cells: list[dict] = []
    for tr in tbl.findall(_hp("tr")):
        for tc in tr.findall(_hp("tc")):
            cells.append(_parse_cell(tc))

    grid = _build_grid(cells, row_count, col_count)
    content = "\n".join(" | ".join(row) for row in grid)
    meta: dict = {
        "headers": [],
        "rows": grid,
        "cells": cells,
        "col_count": col_count,
        "row_count": row_count,
    }
    return Block(type=BlockType.TABLE, content=content, meta=meta)


# ---------------------------------------------------------------------------
# Paragraph parsing  (hp:p -> PARAGRAPH / TABLE blocks in document order)
# ---------------------------------------------------------------------------

def _parse_paragraph(p: ET.Element, blocks: list[Block]) -> None:
    """Append blocks for one ``hp:p``: inline text runs plus any ``hp:tbl``.

    Runs are visited in document order; text accumulates until a table run is
    reached, at which point the buffered paragraph is flushed before the table.
    """
    text_parts: list[str] = []

    def flush() -> None:
        text = "".join(text_parts).strip()
        if text:
            blocks.append(Block(type=BlockType.PARAGRAPH, content=text, meta={}))
        text_parts.clear()

    for run in p.findall(_hp("run")):
        tbl = run.find(_hp("tbl"))
        if tbl is not None:
            flush()
            blocks.append(_parse_table(tbl))
            continue
        text_parts.append(_text_excluding_tables(run))

    flush()


def _page_layout(root: ET.Element) -> dict | None:
    """Extract page dimensions/margins from ``hp:pagePr`` (hwp.py meta shape)."""
    page_pr = next(root.iter(_hp("pagePr")), None)
    if page_pr is None:
        return None
    layout: dict = {
        "width_mm": _to_mm(_as_int(page_pr.get("width"))),
        "height_mm": _to_mm(_as_int(page_pr.get("height"))),
    }
    landscape = page_pr.get("landscape")
    if landscape:
        layout["landscape"] = landscape
    margin = page_pr.find(_hp("margin"))
    if margin is not None:
        layout["margin_left_mm"] = _to_mm(_as_int(margin.get("left")))
        layout["margin_right_mm"] = _to_mm(_as_int(margin.get("right")))
        layout["margin_top_mm"] = _to_mm(_as_int(margin.get("top")))
        layout["margin_bottom_mm"] = _to_mm(_as_int(margin.get("bottom")))
    return layout


def _parse_section(xml_bytes: bytes) -> tuple[Page, dict | None]:
    """Parse one ``sectionN.xml`` into a Page plus its page layout (if any)."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise ValueError(f"Corrupt HWPX section XML: {exc}") from exc

    blocks: list[Block] = []
    for p in root.findall(_hp("p")):
        _parse_paragraph(p, blocks)
    return Page(blocks=blocks), _page_layout(root)


# ---------------------------------------------------------------------------
# Container handling
# ---------------------------------------------------------------------------

def _open_zip(content: bytes) -> zipfile.ZipFile:
    """Open the HWPX zip container, raising ValueError for non-zip input."""
    try:
        return zipfile.ZipFile(BytesIO(content))
    except zipfile.BadZipFile as exc:
        raise ValueError(f"Not a valid HWPX (zip) container: {exc}") from exc


def _check_mimetype(zf: zipfile.ZipFile) -> None:
    """Verify the container declares ``application/hwp+zip``."""
    try:
        mimetype = zf.read("mimetype").decode("ascii", errors="replace").strip()
    except KeyError as exc:
        raise ValueError("HWPX container is missing its mimetype entry") from exc
    if mimetype != _MIMETYPE:
        raise ValueError(f"Unexpected HWPX mimetype: {mimetype!r}")


def _check_not_encrypted(zf: zipfile.ZipFile) -> None:
    """Reject encrypted HWPX (manifest declares per-entry encryption-data)."""
    if "META-INF/manifest.xml" not in zf.namelist():
        return
    manifest = zf.read("META-INF/manifest.xml").decode("utf-8", errors="replace")
    if "encryption-data" in manifest:
        raise ValueError("Encrypted HWPX documents are not supported")


def _list_sections(zf: zipfile.ZipFile) -> list[str]:
    """Return ``Contents/sectionN.xml`` entries sorted by section number."""
    sections = [
        name
        for name in zf.namelist()
        if name.startswith("Contents/section") and name.endswith(".xml")
    ]

    def section_index(name: str) -> int:
        stem = name[len("Contents/section"):-len(".xml")]
        return _as_int(stem)

    return sorted(sections, key=section_index)


def _detect_images(zf: zipfile.ZipFile) -> list[str]:
    """Return BinData/ image entry basenames, matching hwp.py's image list."""
    return sorted(
        name.split("/", 1)[1]
        for name in zf.namelist()
        if name.startswith("BinData/") and not name.endswith("/")
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class HWPXParser:
    """Parse HWPX (open OWPML) documents into UniversalDoc."""

    def parse_bytes(self, content: bytes) -> UniversalDoc:
        zf = _open_zip(content)
        try:
            _check_mimetype(zf)
            _check_not_encrypted(zf)

            pages: list[Page] = []
            page_layout: dict | None = None
            for name in _list_sections(zf):
                page, layout = _parse_section(zf.read(name))
                pages.append(page)
                if layout and page_layout is None:
                    page_layout = layout

            metadata: dict = {}
            images = _detect_images(zf)
            if images:
                metadata["images"] = images
            if page_layout:
                metadata["page_layout"] = page_layout

            return UniversalDoc(pages=pages, metadata=metadata)
        finally:
            zf.close()
