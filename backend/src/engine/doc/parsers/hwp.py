"""HWP 5.x parser — converts HWP documents to UniversalDoc.

Handles OLE2 container, zlib-compressed sections, HWP record parsing,
and text/table/style extraction.  Pure stdlib (struct, zlib).
"""
from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass, field

from src.engine.doc.models import Block, BlockType, Page, UniversalDoc
from src.engine.doc.parsers._ole2 import read_ole2

# ---------------------------------------------------------------------------
# HWP record tag constants (HWPTAG_BEGIN = 16)
# ---------------------------------------------------------------------------
_HWPTAG_BEGIN = 16
_FACE_NAME = _HWPTAG_BEGIN + 3       # 19 — DocInfo font name
_CHAR_SHAPE = _HWPTAG_BEGIN + 5      # 21 — DocInfo character style
_PARA_SHAPE = _HWPTAG_BEGIN + 9      # 25 — DocInfo paragraph style
_PARA_HEADER = _HWPTAG_BEGIN + 50    # 66
_PARA_TEXT = _HWPTAG_BEGIN + 51      # 67
_PARA_CHAR_SHAPE = _HWPTAG_BEGIN + 52  # 68
_CTRL_HEADER = _HWPTAG_BEGIN + 55    # 71
_LIST_HEADER = _HWPTAG_BEGIN + 56    # 72
_PAGE_DEF = _HWPTAG_BEGIN + 57       # 73
_TABLE = _HWPTAG_BEGIN + 61          # 77

# Extended control characters occupy 16 bytes (8 x uint16) in PARA_TEXT
_EXTENDED_CONTROLS: frozenset[int] = frozenset(
    {1, 2, 3, 11, 12, 13, 14, 15, 16, 17, 18, 21, 22, 23}
)

_ALIGN_MAP: dict[int, str] = {0: "justify", 1: "left", 2: "right", 3: "center"}


# ---------------------------------------------------------------------------
# Internal data types
# ---------------------------------------------------------------------------
@dataclass
class _HWPRecord:
    tag: int
    level: int
    data: bytes


@dataclass
class _FileHeader:
    compressed: bool
    encrypted: bool


@dataclass
class _TableInfo:
    rows: int
    cols: int


@dataclass
class _DocStyle:
    """Parsed DocInfo: font table, character shapes, paragraph shapes."""
    fonts: list[str] = field(default_factory=list)
    char_shapes: list[dict] = field(default_factory=list)
    para_shapes: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Low-level parsing
# ---------------------------------------------------------------------------

def _parse_file_header(raw: bytes) -> _FileHeader:
    """Parse the FileHeader stream — check signature, compression, encryption."""
    sig = raw[:17]
    if sig != b"HWP Document File":
        raise ValueError(f"Invalid HWP signature: {sig!r}")
    props = struct.unpack_from("<I", raw, 36)[0]
    return _FileHeader(
        compressed=bool(props & 0x01),
        encrypted=bool(props & 0x02),
    )


def _parse_records(data: bytes) -> list[_HWPRecord]:
    """Parse a decompressed section stream into a flat list of HWP records."""
    records: list[_HWPRecord] = []
    pos = 0
    while pos < len(data):
        if pos + 4 > len(data):
            break
        hdr = struct.unpack_from("<I", data, pos)[0]
        tag = hdr & 0x3FF
        level = (hdr >> 10) & 0x3FF
        size = (hdr >> 20) & 0xFFF
        pos += 4
        if size == 0xFFF:
            if pos + 4 > len(data):
                break
            size = struct.unpack_from("<I", data, pos)[0]
            pos += 4
        rec_data = data[pos : pos + size]
        pos += size
        records.append(_HWPRecord(tag=tag, level=level, data=rec_data))
    return records


def _extract_text(para_text_data: bytes) -> str:
    """Decode PARA_TEXT data: UTF-16LE with control character handling."""
    chars: list[str] = []
    j = 0
    length = len(para_text_data)
    while j < length - 1:
        ch = struct.unpack_from("<H", para_text_data, j)[0]
        if ch in _EXTENDED_CONTROLS:
            j += 16  # 8 uint16 = 16 bytes total
        elif ch < 0x20:
            # Non-extended controls: line break (10), tab (9), etc.
            if ch == 10:
                chars.append("\n")
            j += 2
        else:
            chars.append(chr(ch))
            j += 2
    return "".join(chars)


# ---------------------------------------------------------------------------
# DocInfo parsing — fonts, char shapes, para shapes
# ---------------------------------------------------------------------------

def _parse_doc_info(data: bytes) -> _DocStyle:
    """Parse DocInfo stream to extract font table, char shapes, and para shapes."""
    records = _parse_records(data)
    fonts: list[str] = []
    char_shapes: list[dict] = []
    para_shapes: list[dict] = []

    for rec in records:
        if rec.tag == _FACE_NAME:
            if len(rec.data) < 3:
                continue
            name_len = struct.unpack_from("<H", rec.data, 1)[0]
            end = 3 + name_len * 2
            if end <= len(rec.data):
                name = rec.data[3:end].decode("utf-16-le", errors="replace")
                fonts.append(name)

        elif rec.tag == _CHAR_SHAPE:
            if len(rec.data) < 56:
                continue
            face_id = struct.unpack_from("<H", rec.data, 0)[0]
            height = struct.unpack_from("<I", rec.data, 42)[0]
            prop = struct.unpack_from("<I", rec.data, 46)[0]
            color_raw = struct.unpack_from("<I", rec.data, 52)[0]

            b_val = color_raw & 0xFF
            g_val = (color_raw >> 8) & 0xFF
            r_val = (color_raw >> 16) & 0xFF

            char_shapes.append({
                "face_id": face_id,
                "height": height,
                "bold": bool(prop & 0x01),
                "italic": bool(prop & 0x02),
                "underline": bool((prop >> 2) & 0x07),
                "color": f"#{r_val:02x}{g_val:02x}{b_val:02x}",
            })

        elif rec.tag == _PARA_SHAPE:
            if len(rec.data) < 28:
                continue
            prop = struct.unpack_from("<I", rec.data, 0)[0]
            align_val = (prop >> 2) & 0x07
            line_spacing = struct.unpack_from("<i", rec.data, 24)[0]

            para_shapes.append({
                "align": _ALIGN_MAP.get(align_val, "left"),
                "line_spacing": line_spacing,
            })

    return _DocStyle(fonts=fonts, char_shapes=char_shapes, para_shapes=para_shapes)


def _parse_char_shape_pairs(data: bytes) -> list[tuple[int, int]]:
    """Parse PARA_CHAR_SHAPE: array of (position, charShapeID) pairs."""
    pairs: list[tuple[int, int]] = []
    i = 0
    while i + 8 <= len(data):
        pos = struct.unpack_from("<I", data, i)[0]
        cs_id = struct.unpack_from("<I", data, i + 4)[0]
        pairs.append((pos, cs_id))
        i += 8
    return pairs


def _build_para_style(
    doc_style: _DocStyle | None,
    para_shape_id: int | None,
    char_shape_ids: list[tuple[int, int]],
) -> dict:
    """Build style dict from DocStyle lookups."""
    if doc_style is None:
        return {}
    style: dict = {}

    if para_shape_id is not None and para_shape_id < len(doc_style.para_shapes):
        ps = doc_style.para_shapes[para_shape_id]
        style["align"] = ps["align"]
        style["line_spacing"] = ps["line_spacing"]

    if char_shape_ids:
        cs_id = char_shape_ids[0][1]
        if cs_id < len(doc_style.char_shapes):
            cs = doc_style.char_shapes[cs_id]
            style["bold"] = cs["bold"]
            style["italic"] = cs["italic"]
            style["underline"] = cs["underline"]
            style["color"] = cs["color"]
            style["size"] = cs["height"] / 100
            font_id = cs["face_id"]
            if font_id < len(doc_style.fonts):
                style["font"] = doc_style.fonts[font_id]

    return style


def _parse_page_def(data: bytes) -> dict:
    """Parse PAGE_DEF record: page dimensions and margins in HWP units -> mm."""
    if len(data) < 36:
        return {}
    values = struct.unpack_from("<9I", data, 0)

    def to_mm(v: int) -> float:
        return round(v / 7200 * 25.4, 1)

    return {
        "width_mm": to_mm(values[0]),
        "height_mm": to_mm(values[1]),
        "margin_left_mm": to_mm(values[2]),
        "margin_right_mm": to_mm(values[3]),
        "margin_top_mm": to_mm(values[4]),
        "margin_bottom_mm": to_mm(values[5]),
    }


def _parse_list_header_cell(data: bytes) -> dict:
    """Extract cell metadata from LIST_HEADER record."""
    cell: dict = {}
    if len(data) >= 24:
        cell["col"] = struct.unpack_from("<H", data, 8)[0]
        cell["row"] = struct.unpack_from("<H", data, 10)[0]
        cell["colspan"] = struct.unpack_from("<H", data, 12)[0]
        cell["rowspan"] = struct.unpack_from("<H", data, 14)[0]
        width = struct.unpack_from("<I", data, 16)[0]
        height = struct.unpack_from("<I", data, 20)[0]
        cell["width_mm"] = round(width / 7200 * 25.4, 1)
        cell["height_mm"] = round(height / 7200 * 25.4, 1)
    return cell


# ---------------------------------------------------------------------------
# Record tree -> Blocks
# ---------------------------------------------------------------------------

def _records_to_page(
    records: list[_HWPRecord],
    doc_style: _DocStyle | None = None,
) -> tuple[Page, dict | None]:
    """Convert a flat record list (one section) to a Page of blocks."""
    blocks: list[Block] = []
    i = 0
    n = len(records)
    current_para_shape_id: int | None = None
    current_char_shape_ids: list[tuple[int, int]] = []
    page_layout: dict | None = None

    while i < n:
        rec = records[i]

        if rec.tag == _PAGE_DEF:
            page_layout = _parse_page_def(rec.data)
            i += 1
            continue

        if rec.tag == _PARA_HEADER and rec.level <= 1:
            if len(rec.data) >= 10:
                current_para_shape_id = struct.unpack_from("<H", rec.data, 8)[0]
            i += 1
            continue

        if rec.tag == _PARA_CHAR_SHAPE and rec.level <= 2:
            current_char_shape_ids = _parse_char_shape_pairs(rec.data)
            i += 1
            continue

        # Top-level PARA_TEXT -> PARAGRAPH block
        if rec.tag == _PARA_TEXT and rec.level <= 1:
            text = _extract_text(rec.data).strip()
            if text:
                style = _build_para_style(
                    doc_style, current_para_shape_id, current_char_shape_ids,
                )
                meta = {"style": style} if style else {}
                blocks.append(Block(type=BlockType.PARAGRAPH, content=text, meta=meta))
            current_para_shape_id = None
            current_char_shape_ids = []
            i += 1
            continue

        # TABLE structure: CTRL_HEADER at level 1 followed by TABLE record
        if rec.tag == _CTRL_HEADER and rec.level == 1:
            table_info = _find_table(records, i)
            if table_info is not None:
                table_block, end_idx = _parse_table_block(
                    records, i, table_info, doc_style,
                )
                blocks.append(table_block)
                current_para_shape_id = None
                current_char_shape_ids = []
                i = end_idx
                continue
            i += 1
            continue

        i += 1

    return Page(blocks=blocks), page_layout


def _find_table(records: list[_HWPRecord], ctrl_idx: int) -> _TableInfo | None:
    """Check if CTRL_HEADER at *ctrl_idx* is a table; return info if so."""
    ctrl_level = records[ctrl_idx].level
    for j in range(ctrl_idx + 1, min(ctrl_idx + 5, len(records))):
        r = records[j]
        if r.level <= ctrl_level:
            break
        if r.tag == _TABLE:
            # TABLE record: first 4 bytes = flags, next 2 = rows, next 2 = cols
            if len(r.data) >= 8:
                rows = struct.unpack_from("<H", r.data, 4)[0]
                cols = struct.unpack_from("<H", r.data, 6)[0]
                return _TableInfo(rows=rows, cols=cols)
            return _TableInfo(rows=0, cols=0)
    return None


def _parse_table_block(
    records: list[_HWPRecord],
    ctrl_idx: int,
    info: _TableInfo,
    doc_style: _DocStyle | None = None,
) -> tuple[Block, int]:
    """Extract cell texts and structure from a table and return (Block, end_index)."""
    ctrl_level = records[ctrl_idx].level
    cells: list[dict] = []
    i = ctrl_idx + 1
    n = len(records)

    while i < n:
        r = records[i]
        if r.level <= ctrl_level:
            break

        # LIST_HEADER marks a cell boundary
        if r.tag == _LIST_HEADER and r.level == ctrl_level + 1:
            cell_meta = _parse_list_header_cell(r.data)

            # Collect text and style within this cell
            cell_parts: list[str] = []
            cell_style: dict = {}
            j = i + 1
            while j < n:
                rr = records[j]
                if rr.level <= ctrl_level:
                    break
                if rr.tag == _LIST_HEADER and rr.level == ctrl_level + 1:
                    break
                if rr.tag == _PARA_HEADER and doc_style and len(rr.data) >= 10:
                    ps_id = struct.unpack_from("<H", rr.data, 8)[0]
                    if ps_id < len(doc_style.para_shapes):
                        cell_style.update(doc_style.para_shapes[ps_id])
                if rr.tag == _PARA_CHAR_SHAPE and doc_style:
                    pairs = _parse_char_shape_pairs(rr.data)
                    if pairs:
                        cs_id = pairs[0][1]
                        if cs_id < len(doc_style.char_shapes):
                            cs = doc_style.char_shapes[cs_id]
                            cell_style["bold"] = cs["bold"]
                            cell_style["italic"] = cs["italic"]
                            cell_style["color"] = cs["color"]
                            cell_style["size"] = cs["height"] / 100
                            if cs["face_id"] < len(doc_style.fonts):
                                cell_style["font"] = doc_style.fonts[cs["face_id"]]
                if rr.tag == _PARA_TEXT:
                    text = _extract_text(rr.data).strip()
                    if text:
                        cell_parts.append(text)
                j += 1

            cell_meta["text"] = " ".join(cell_parts)
            if cell_style:
                cell_meta["style"] = cell_style
            cells.append(cell_meta)
            i = j
            continue
        i += 1

    # Build legacy grid format + enriched cells
    cell_texts = [c.get("text", "") for c in cells]
    grid_rows = _cells_to_grid(cell_texts, info.cols)
    content = "\n".join(" | ".join(row) for row in grid_rows)
    meta: dict = {
        "headers": [],
        "rows": grid_rows,
        "cells": cells,
        "col_count": info.cols,
        "row_count": info.rows,
    }

    return Block(type=BlockType.TABLE, content=content, meta=meta), i


def _cells_to_grid(cells: list[str], cols: int) -> list[list[str]]:
    """Split flat cell list into a list of rows (list of list of str)."""
    if cols <= 0:
        return [[c] for c in cells] if cells else []
    rows: list[list[str]] = []
    for i in range(0, len(cells), cols):
        rows.append(cells[i : i + cols])
    return rows


# ---------------------------------------------------------------------------
# Image detection
# ---------------------------------------------------------------------------

def _detect_images(streams: dict[str, bytes]) -> list[str]:
    """Return list of image filenames found in BinData/."""
    images: list[str] = []
    for name in sorted(streams):
        if name.startswith("BinData/"):
            images.append(name.split("/", 1)[1])
    return images


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class HWPParser:
    """Parse HWP 5.x binary files into UniversalDoc."""

    def parse_bytes(self, content: bytes) -> UniversalDoc:
        ole = read_ole2(content)

        # FileHeader
        if "FileHeader" not in ole.streams:
            raise ValueError("Missing FileHeader in HWP document")
        header = _parse_file_header(ole.streams["FileHeader"])

        if header.encrypted:
            raise ValueError("Encrypted HWP documents are not supported")

        # DocInfo -> styles
        doc_style: _DocStyle | None = None
        if "DocInfo" in ole.streams:
            raw = ole.streams["DocInfo"]
            if header.compressed:
                raw = zlib.decompress(raw, -15)
            doc_style = _parse_doc_info(raw)

        # Sections
        section_keys = sorted(
            k for k in ole.streams if k.startswith("BodyText/Section")
        )
        pages: list[Page] = []
        page_layout: dict | None = None
        for key in section_keys:
            raw = ole.streams[key]
            body = zlib.decompress(raw, -15) if header.compressed else raw
            records = _parse_records(body)
            page, layout = _records_to_page(records, doc_style)
            pages.append(page)
            if layout and page_layout is None:
                page_layout = layout

        # Metadata
        metadata: dict = {}
        images = _detect_images(ole.streams)
        if images:
            metadata["images"] = images
        if page_layout:
            metadata["page_layout"] = page_layout

        return UniversalDoc(pages=pages, metadata=metadata)
