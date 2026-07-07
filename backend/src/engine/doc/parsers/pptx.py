"""PPTX (OOXML) parser — converts PowerPoint .pptx presentations to UniversalDoc.

A .pptx file is a ZIP container of XML parts.  Slide order is declared in
``ppt/presentation.xml`` under ``p:sldIdLst`` (a list of ``p:sldId`` elements,
each referencing a relationship id ``r:id``); the relationship ids are resolved
to slide part paths via ``ppt/_rels/presentation.xml.rels``.  The slide bodies
live in ``ppt/slides/slideN.xml`` under the DrawingML (``a:``) and
PresentationML (``p:``) namespaces.  This parser is pure stdlib (``zipfile`` +
``xml.etree.ElementTree``); no ``python-pptx`` or other third-party dependency.

Scope (v1)
----------
- Each slide maps 1:1 to a :class:`Page`, in ``p:sldIdLst`` order (NOT ZIP entry
  order), resolved through the presentation relationships.
- Text: shapes (``p:sp``) carry a ``p:txBody`` of paragraphs (``a:p``) whose runs
  (``a:r``/``a:t``, plus ``a:fld`` fields and ``a:br`` breaks) hold the text.  A
  shape whose placeholder (``p:ph``) is ``title``/``ctrTitle`` becomes a single
  HEADING (level 1); every other text frame emits one PARAGRAPH per non-empty
  paragraph.  List indentation (``a:pPr@lvl``) is ignored in v1 — TODO.
- Tables (``a:tbl`` inside a ``p:graphicFrame``) become a TABLE block.  DrawingML
  emits one ``a:tc`` per grid column; the merge origin carries ``gridSpan`` /
  ``rowSpan`` and the covered cells carry ``hMerge`` / ``vMerge`` flags (skipped).
  The ``meta`` shape (``headers``/``rows``/``cells``) matches the HWP parser so the
  serializer / viewer render it unchanged.
- ``ppt/media/*`` entries are listed by basename in ``metadata["images"]``.
- Slide dimensions (``p:sldSz``) become ``metadata["page_layout"]`` in mm
  (EMU -> mm: ``/914400*25.4``).
- A non-ZIP payload or a corrupt/incomplete archive raises :class:`ValueError`.
"""
from __future__ import annotations

import io
import posixpath
import zipfile
from xml.etree import ElementTree as ET

from src.engine.doc.models import Block, BlockType, Page, UniversalDoc

# ── OOXML namespaces ──────────────────────────────────────────
_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
_P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
_R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_PKG_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"

_PRESENTATION_PART = "ppt/presentation.xml"
_PRESENTATION_RELS = "ppt/_rels/presentation.xml.rels"
_SLIDE_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide"
_MEDIA_PREFIX = "ppt/media/"

_TITLE_PH_TYPES = frozenset({"title", "ctrTitle"})
_EMU_PER_MM = 914400 / 25.4  # 36000 EMU == 1 mm


# ── small XML helpers ─────────────────────────────────────────

def _local(tag: str) -> str:
    """Return the local (namespace-stripped) name of an element tag."""
    return tag.rsplit("}", 1)[-1]


def _to_mm(emu: int | None) -> float | None:
    """Convert an EMU length to millimetres (rounded), or None."""
    if emu is None:
        return None
    return round(emu / _EMU_PER_MM, 1)


# ── presentation ordering (sldIdLst -> rels -> slide paths) ───

def _slide_order(pres_xml: bytes, rels_xml: bytes | None) -> list[str]:
    """Resolve the ordered list of slide part paths from the presentation.

    Reads ``p:sldIdLst`` for the authoritative slide sequence (a list of
    ``r:id`` references) and maps each id to a part path via the presentation
    relationships.  Ids that do not resolve to a slide part are skipped.
    """
    rel_targets = _parse_rels(rels_xml)
    try:
        root = ET.fromstring(pres_xml)
    except ET.ParseError as exc:
        raise ValueError(f"Corrupt ppt/presentation.xml: {exc}") from exc

    order: list[str] = []
    lst = root.find(_P + "sldIdLst")
    if lst is None:
        return order
    for sld in lst.findall(_P + "sldId"):
        rid = sld.get(_R + "id")
        if rid is None:
            continue
        target = rel_targets.get(rid)
        if target is not None:
            order.append(target)
    return order


def _parse_rels(rels_xml: bytes | None) -> dict[str, str]:
    """Map each slide relationship id to its normalised part path (under ppt/)."""
    targets: dict[str, str] = {}
    if not rels_xml:
        return targets
    try:
        root = ET.fromstring(rels_xml)
    except ET.ParseError:
        return targets
    for rel in root.findall(_PKG_REL + "Relationship"):
        if rel.get("Type") != _SLIDE_REL_TYPE:
            continue
        rid = rel.get("Id")
        target = rel.get("Target")
        if not rid or not target:
            continue
        # Targets are relative to ppt/ (the presentation part's directory).
        targets[rid] = posixpath.normpath(posixpath.join("ppt", target))
    return targets


def _slide_size(pres_xml: bytes) -> dict | None:
    """Extract ``p:sldSz`` slide dimensions as a mm page layout, if present."""
    try:
        root = ET.fromstring(pres_xml)
    except ET.ParseError:
        return None
    sz = root.find(_P + "sldSz")
    if sz is None:
        return None

    def _dim(attr: str) -> int | None:
        v = sz.get(attr)
        try:
            return int(v) if v is not None else None
        except ValueError:
            return None

    width = _to_mm(_dim("cx"))
    height = _to_mm(_dim("cy"))
    if width is None and height is None:
        return None
    return {"width_mm": width, "height_mm": height}


# ── text extraction (paragraphs / runs) ───────────────────────

def _paragraph_text(p: ET.Element) -> str:
    """Concatenate the visible text of a paragraph (runs, fields, line breaks)."""
    parts: list[str] = []
    for child in p:
        tag = _local(child.tag)
        if tag in ("r", "fld"):
            parts.append("".join(t.text or "" for t in child.iter(_A + "t")))
        elif tag == "br":
            parts.append("\n")
    return "".join(parts)


def _placeholder_type(sp: ET.Element) -> str | None:
    """Return the placeholder type of a shape (``p:ph@type``), if any."""
    nv = sp.find(_P + "nvSpPr")
    if nv is None:
        return None
    nvpr = nv.find(_P + "nvPr")
    if nvpr is None:
        return None
    ph = nvpr.find(_P + "ph")
    if ph is None:
        return None
    return ph.get("type")


def _shape_blocks(sp: ET.Element) -> list[Block]:
    """Convert a text shape (``p:sp``) into HEADING/PARAGRAPH blocks."""
    tx = sp.find(_P + "txBody")
    if tx is None:
        return []
    paragraphs = tx.findall(_A + "p")
    texts = [_paragraph_text(p).strip() for p in paragraphs]
    texts = [t for t in texts if t]
    if not texts:
        return []

    if _placeholder_type(sp) in _TITLE_PH_TYPES:
        # Title placeholder -> a single level-1 heading.
        return [
            Block(
                type=BlockType.HEADING,
                content="\n".join(texts),
                meta={"level": 1},
            )
        ]

    return [Block(type=BlockType.PARAGRAPH, content=t, meta={}) for t in texts]


# ── table parsing (a:tbl -> TABLE) ────────────────────────────

def _cell_text(tc: ET.Element) -> str:
    """Plain text of a table cell: paragraph texts joined by newlines.

    Cell paragraphs live under the cell's ``a:txBody`` (not directly under
    ``a:tc``), so descend into it before collecting paragraphs.
    """
    body = tc.find(_A + "txBody")
    if body is None:
        return ""
    lines: list[str] = []
    for p in body.findall(_A + "p"):
        text = _paragraph_text(p).strip()
        if text:
            lines.append(text)
    return "\n".join(lines)


def _parse_table(tbl: ET.Element) -> Block:
    """Convert an ``a:tbl`` into a TABLE block with an HWP-compatible cell grid.

    DrawingML emits one ``a:tc`` per grid column; the merge origin carries
    ``gridSpan`` (colspan) / ``rowSpan``, while covered cells carry ``hMerge`` /
    ``vMerge`` flags and are skipped (the origin's span already describes them).
    """
    rows = tbl.findall(_A + "tr")
    cells: list[dict] = []
    col_count = 0

    for r, tr in enumerate(rows):
        c = 0
        for tc in tr.findall(_A + "tc"):
            if tc.get("hMerge") == "1" or tc.get("vMerge") == "1":
                c += 1  # continuation of a merged region — occupies a grid slot
                continue
            cells.append({
                "text": _cell_text(tc),
                "row": r,
                "col": c,
                "colspan": _int_attr(tc, "gridSpan"),
                "rowspan": _int_attr(tc, "rowSpan"),
            })
            c += 1
        col_count = max(col_count, c)

    grid_rows = _cells_to_grid(cells, len(rows), col_count)
    content = "\n".join(" | ".join(row) for row in grid_rows)
    meta = {
        "headers": [],
        "rows": grid_rows,
        "cells": cells,
        "col_count": col_count,
        "row_count": len(rows),
    }
    return Block(type=BlockType.TABLE, content=content, meta=meta)


def _int_attr(tc: ET.Element, name: str) -> int:
    """Return a positive integer span attribute (``gridSpan``/``rowSpan``), or 1."""
    v = tc.get(name)
    try:
        return max(1, int(v)) if v is not None else 1
    except ValueError:
        return 1


def _cells_to_grid(cells: list[dict], row_count: int, col_count: int) -> list[list[str]]:
    """Render cells into a dense text grid (merge origins placed at their slot)."""
    grid = [["" for _ in range(col_count)] for _ in range(row_count)]
    for cell in cells:
        r, c = cell["row"], cell["col"]
        if 0 <= r < row_count and 0 <= c < col_count:
            grid[r][c] = cell["text"].replace("\n", " ")
    return grid


# ── slide -> Page (document-order shape traversal) ────────────

def _slide_to_page(slide_xml: bytes) -> Page:
    """Convert a slide part into a Page of blocks, in shape (document) order."""
    try:
        root = ET.fromstring(slide_xml)
    except ET.ParseError as exc:
        raise ValueError(f"Corrupt slide XML: {exc}") from exc

    tree = root.find(_P + "cSld")
    tree = tree.find(_P + "spTree") if tree is not None else None
    if tree is None:
        return Page(blocks=[])

    blocks: list[Block] = []
    _collect_blocks(tree, blocks)
    return Page(blocks=blocks)


def _collect_blocks(parent: ET.Element, blocks: list[Block]) -> None:
    """Walk a shape-tree, emitting blocks for text shapes and tables in order.

    Group shapes (``p:grpSp``) are descended into so their contents surface at
    the group's position in document order.
    """
    for child in parent:
        tag = _local(child.tag)
        if tag == "sp":
            blocks.extend(_shape_blocks(child))
        elif tag == "graphicFrame":
            for tbl in child.iter(_A + "tbl"):
                blocks.append(_parse_table(tbl))
        elif tag == "grpSp":
            _collect_blocks(child, blocks)


# ── public API ────────────────────────────────────────────────

class PPTXParser:
    """Parse PowerPoint .pptx (OOXML) presentations into a UniversalDoc."""

    def parse_bytes(self, content: bytes) -> UniversalDoc:
        try:
            archive = zipfile.ZipFile(io.BytesIO(content))
        except zipfile.BadZipFile as exc:
            # Non-ZIP payload: corrupt file or an encrypted (OLE) .pptx.
            raise ValueError(f"Not a valid PPTX (ZIP) file: {exc}") from exc

        with archive:
            names = set(archive.namelist())
            if _PRESENTATION_PART not in names:
                raise ValueError("Missing ppt/presentation.xml in PPTX")

            pres_xml = archive.read(_PRESENTATION_PART)
            rels_xml = (
                archive.read(_PRESENTATION_RELS)
                if _PRESENTATION_RELS in names
                else None
            )

            order = _slide_order(pres_xml, rels_xml)
            pages: list[Page] = []
            for path in order:
                if path in names:
                    pages.append(_slide_to_page(archive.read(path)))

            images = sorted(
                name[len(_MEDIA_PREFIX):]
                for name in names
                if name.startswith(_MEDIA_PREFIX) and not name.endswith("/")
            )

        metadata: dict = {}
        if images:
            metadata["images"] = images
        page_layout = _slide_size(pres_xml)
        if page_layout:
            metadata["page_layout"] = page_layout

        return UniversalDoc(pages=pages, metadata=metadata)
