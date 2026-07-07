"""DOCX (OOXML) parser — converts Word .docx documents to UniversalDoc.

A .docx file is a ZIP container of XML parts.  The body lives in
``word/document.xml`` under the ``w:`` (wordprocessingml) namespace.  This
parser is pure stdlib (``zipfile`` + ``xml.etree.ElementTree``); no
``python-docx`` or other third-party dependency.

Scope (v1)
----------
- DOCX has no intrinsic page concept (it is a reflowable flow), so every block
  goes onto a single :class:`Page`.  Explicit page breaks (``w:br`` type=page)
  are ignored in v1.
- ``w:p`` -> HEADING when its ``w:pStyle`` resolves (via ``word/styles.xml``) to
  a ``heading N`` style, otherwise PARAGRAPH.  Consecutive ``w:numPr``
  paragraphs collapse into one LIST block.
- Run formatting (``w:b``/``w:i``/``w:u``) is emitted as the canonical inline
  whitelist (``strong``/``em``/``u``); combinations nest.
- ``w:tbl`` -> TABLE with ``gridSpan`` (colspan) and ``vMerge`` (rowspan)
  honoured; the ``meta["cells"]`` shape matches the HWP parser so the dialect
  serializer / viewer render it unchanged.
- ``word/media/*`` entries are listed by name in ``metadata["images"]``.
- A non-ZIP payload (e.g. an OLE-encrypted .docx) or a corrupt archive raises
  :class:`ValueError`.
"""
from __future__ import annotations

import io
import re
import zipfile
from html import escape
from xml.etree import ElementTree as ET

from src.engine.doc.models import Block, BlockType, Page, UniversalDoc

# ── OOXML namespace ───────────────────────────────────────────
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

_DOCUMENT_PART = "word/document.xml"
_STYLES_PART = "word/styles.xml"
_MEDIA_PREFIX = "word/media/"

_HEADING_RE = re.compile(r"heading\s*([1-9])", re.IGNORECASE)

# ``w:val`` values that mean "toggle off" for boolean run properties.
_FALSY_VALS = frozenset({"0", "false", "off", "none"})


# ── small XML helpers ─────────────────────────────────────────

def _local(tag: str) -> str:
    """Return the local (namespace-stripped) name of an element tag."""
    return tag.rsplit("}", 1)[-1]


def _val(elem: ET.Element | None) -> str | None:
    """Return the ``w:val`` attribute of *elem* (or None)."""
    if elem is None:
        return None
    return elem.get(_W + "val")


def _toggle_on(rpr: ET.Element | None, name: str) -> bool:
    """True if boolean run property *name* is present and not toggled off."""
    if rpr is None:
        return False
    el = rpr.find(_W + name)
    if el is None:
        return False
    v = _val(el)
    return v is None or v.lower() not in _FALSY_VALS


# ── styles.xml — styleId -> heading level ─────────────────────

def _build_style_headings(styles_xml: bytes | None) -> dict[str, int]:
    """Map each paragraph styleId to a heading level (1-6) where applicable.

    A style is a heading when its ``w:name`` matches ``heading N``.  Styles such
    as ``header``/``Title``/``TOC`` deliberately do not match.
    """
    headings: dict[str, int] = {}
    if not styles_xml:
        return headings
    try:
        root = ET.fromstring(styles_xml)
    except ET.ParseError:
        return headings
    for style in root.findall(_W + "style"):
        style_id = style.get(_W + "styleId")
        if not style_id:
            continue
        level = _heading_level_from_name(_val(style.find(_W + "name")) or "")
        if level is not None:
            headings[style_id] = level
    return headings


def _heading_level_from_name(name: str) -> int | None:
    """Extract a clamped heading level (1-6) from a style *name*, else None."""
    m = _HEADING_RE.match(name.strip())
    if m is None:
        return None
    return min(6, int(m.group(1)))


def _paragraph_heading_level(
    style_id: str | None, style_headings: dict[str, int]
) -> int | None:
    """Resolve a paragraph's ``w:pStyle`` to a heading level, if any.

    Falls back to matching the styleId itself (covers English Word where the
    id *is* ``Heading1``) when styles.xml did not resolve it.
    """
    if style_id is None:
        return None
    if style_id in style_headings:
        return style_headings[style_id]
    return _heading_level_from_name(style_id)


# ── run / paragraph inline extraction ─────────────────────────

def _run_text(run: ET.Element) -> str:
    """Concatenate the visible text of a run (``w:t``/tab/break), raw."""
    parts: list[str] = []
    for child in run:
        tag = _local(child.tag)
        if tag == "t":
            parts.append(child.text or "")
        elif tag == "tab":
            parts.append("\t")
        elif tag in ("br", "cr"):
            parts.append("\n")
        elif tag == "noBreakHyphen":
            parts.append("-")
    return "".join(parts)


def _run_inline(run: ET.Element) -> str:
    """Render a run to a canonical inline fragment (escaped, formatting nested)."""
    raw = _run_text(run)
    if not raw:
        return ""
    frag = escape(raw)
    rpr = run.find(_W + "rPr")
    if _toggle_on(rpr, "u"):
        frag = f"<u>{frag}</u>"
    if _toggle_on(rpr, "i"):
        frag = f"<em>{frag}</em>"
    if _toggle_on(rpr, "b"):
        frag = f"<strong>{frag}</strong>"
    return frag


def _paragraph_inline(p: ET.Element) -> str:
    """Concatenate inline fragments for every run in *p* (document order)."""
    return "".join(_run_inline(r) for r in p.iter(_W + "r"))


def _paragraph_plaintext(p: ET.Element) -> str:
    """Concatenate the raw text of a paragraph (for emptiness checks / cells)."""
    return "".join(_run_text(r) for r in p.iter(_W + "r"))


def _paragraph_style_id(p: ET.Element) -> str | None:
    ppr = p.find(_W + "pPr")
    if ppr is None:
        return None
    return _val(ppr.find(_W + "pStyle"))


def _paragraph_has_numpr(p: ET.Element) -> bool:
    ppr = p.find(_W + "pPr")
    return ppr is not None and ppr.find(_W + "numPr") is not None


# ── block-level traversal (descends into w:sdt wrappers) ──────

def _iter_block_elements(parent: ET.Element):
    """Yield ``w:p`` and ``w:tbl`` elements in document order.

    Structured-document-tag wrappers (``w:sdt`` — e.g. a table of contents) are
    transparently descended into so their paragraphs/tables surface inline.
    """
    for child in parent:
        tag = _local(child.tag)
        if tag in ("p", "tbl"):
            yield child
        elif tag == "sdt":
            content = child.find(_W + "sdtContent")
            if content is not None:
                yield from _iter_block_elements(content)


# ── table parsing (gridSpan / vMerge) ─────────────────────────

def _cell_colspan(tc: ET.Element) -> int:
    tcpr = tc.find(_W + "tcPr")
    if tcpr is None:
        return 1
    v = _val(tcpr.find(_W + "gridSpan"))
    try:
        return max(1, int(v)) if v is not None else 1
    except ValueError:
        return 1


def _cell_vmerge(tc: ET.Element) -> str | None:
    """Return 'restart', 'continue', or None for a cell's vertical merge state."""
    tcpr = tc.find(_W + "tcPr")
    if tcpr is None:
        return None
    vm = tcpr.find(_W + "vMerge")
    if vm is None:
        return None
    v = _val(vm)
    return "restart" if (v or "").lower() == "restart" else "continue"


def _cell_text(tc: ET.Element) -> str:
    """Plain text of a cell: paragraph texts joined by newlines (raw)."""
    lines: list[str] = []
    for p in _iter_block_elements(tc):
        if _local(p.tag) != "p":
            continue
        text = _paragraph_plaintext(p).strip()
        if text:
            lines.append(text)
    return "\n".join(lines)


def _parse_table(tbl: ET.Element) -> Block:
    """Convert a ``w:tbl`` into a TABLE block with an HWP-compatible cell grid."""
    rows = [r for r in tbl if _local(r.tag) == "tr"]
    cells: list[dict] = []
    col_count = 0
    open_vmerge: dict[int, dict] = {}  # start-column -> restart cell dict

    for r, tr in enumerate(rows):
        c = 0
        for tc in tr:
            if _local(tc.tag) != "tc":
                continue
            colspan = _cell_colspan(tc)
            vmerge = _cell_vmerge(tc)

            if vmerge == "continue":
                # Continuation of a vertical merge: grow the owner's rowspan.
                owner = open_vmerge.get(c)
                if owner is not None:
                    owner["rowspan"] += 1
                c += colspan
                continue

            cell = {
                "text": _cell_text(tc),
                "row": r,
                "col": c,
                "colspan": colspan,
                "rowspan": 1,
            }
            cells.append(cell)
            if vmerge == "restart":
                open_vmerge[c] = cell
            else:
                open_vmerge.pop(c, None)
            c += colspan
            col_count = max(col_count, c)

    content = _table_content(cells, len(rows), col_count)
    meta = {
        "cells": cells,
        "col_count": col_count,
        "row_count": len(rows),
    }
    return Block(type=BlockType.TABLE, content=content, meta=meta)


def _table_content(cells: list[dict], row_count: int, col_count: int) -> str:
    """Render a plain-text preview of the table (one row per line)."""
    grid = [["" for _ in range(col_count)] for _ in range(row_count)]
    for cell in cells:
        r, c = cell["row"], cell["col"]
        if 0 <= r < row_count and 0 <= c < col_count:
            grid[r][c] = cell["text"].replace("\n", " ")
    return "\n".join(" | ".join(row) for row in grid)


# ── document.xml -> Page ──────────────────────────────────────

def _flush_list(items: list[str], blocks: list[Block]) -> None:
    """Emit a pending LIST block from accumulated item fragments."""
    if not items:
        return
    # TODO(v1): numbering.xml is not read, so ordered lists are reported as
    # unordered.  Resolve w:numId -> numbering format for meta["ordered"].
    blocks.append(
        Block(type=BlockType.LIST, content="\n".join(items), meta={"ordered": False})
    )
    items.clear()


def _body_to_page(body: ET.Element, style_headings: dict[str, int]) -> Page:
    """Convert the ``w:body`` element into a single Page of blocks."""
    blocks: list[Block] = []
    list_items: list[str] = []

    for el in _iter_block_elements(body):
        if _local(el.tag) == "tbl":
            _flush_list(list_items, blocks)
            blocks.append(_parse_table(el))
            continue

        # paragraph
        level = _paragraph_heading_level(_paragraph_style_id(el), style_headings)
        plain = _paragraph_plaintext(el).strip()

        if level is not None:
            _flush_list(list_items, blocks)
            if plain:
                blocks.append(
                    Block(
                        type=BlockType.HEADING,
                        content=_paragraph_inline(el),
                        meta={"level": level},
                    )
                )
            continue

        if _paragraph_has_numpr(el):
            if plain:
                list_items.append(_paragraph_inline(el))
            continue

        _flush_list(list_items, blocks)
        if plain:
            blocks.append(
                Block(type=BlockType.PARAGRAPH, content=_paragraph_inline(el), meta={})
            )

    _flush_list(list_items, blocks)
    return Page(blocks=blocks)


# ── public API ────────────────────────────────────────────────

class DOCXParser:
    """Parse Word .docx (OOXML) files into a UniversalDoc."""

    def parse_bytes(self, content: bytes) -> UniversalDoc:
        try:
            archive = zipfile.ZipFile(io.BytesIO(content))
        except zipfile.BadZipFile as exc:
            # Non-ZIP payload: corrupt file or an OLE-encrypted .docx.
            raise ValueError(f"Not a valid DOCX (ZIP) file: {exc}") from exc

        with archive:
            names = set(archive.namelist())
            if _DOCUMENT_PART not in names:
                raise ValueError("Missing word/document.xml in DOCX")

            try:
                doc_root = ET.fromstring(archive.read(_DOCUMENT_PART))
            except ET.ParseError as exc:
                raise ValueError(f"Corrupt word/document.xml: {exc}") from exc

            styles_xml = (
                archive.read(_STYLES_PART) if _STYLES_PART in names else None
            )
            images = sorted(
                name[len(_MEDIA_PREFIX):]
                for name in names
                if name.startswith(_MEDIA_PREFIX) and not name.endswith("/")
            )

        style_headings = _build_style_headings(styles_xml)

        body = doc_root.find(_W + "body")
        page = (
            _body_to_page(body, style_headings)
            if body is not None
            else Page(blocks=[])
        )

        metadata: dict = {}
        if images:
            metadata["images"] = images

        return UniversalDoc(pages=[page], metadata=metadata)
