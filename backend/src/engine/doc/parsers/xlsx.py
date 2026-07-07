"""XLSX (OOXML SpreadsheetML) parser — converts Excel .xlsx workbooks to UniversalDoc.

An .xlsx file is a ZIP container of XML parts under the ``spreadsheetml`` (main)
namespace:

- ``xl/workbook.xml``          — the ordered list of sheets (``<sheet name r:id>``)
- ``xl/_rels/workbook.xml.rels`` — maps each ``r:id`` to a worksheet part path
- ``xl/worksheets/sheetN.xml`` — the cell grid of one sheet (``<sheetData>``)
- ``xl/sharedStrings.xml``     — the deduplicated string pool (cells with ``t="s"``)

This parser is pure stdlib (``zipfile`` + ``xml.etree.ElementTree``); no
``openpyxl`` or other third-party dependency.

Scope (v1)
----------
- Each worksheet maps 1:1 to a :class:`Page` in workbook (``<sheets>``) order.
  The model has no per-page name field, so when the workbook emits **more than
  one** page each page begins with a ``HEADING`` (level 2, the sheet name)
  followed by the ``TABLE``; a lone sheet omits the heading.
- Cell values: shared strings (``t="s"``), inline strings (``t="inlineStr"``),
  formula string / error / date results (``t="str"``/``"e"``/``"d"`` — cached
  ``<v>``), booleans (``t="b"`` -> ``TRUE``/``FALSE``), and numbers (the cached
  ``<v>`` text, kept verbatim so integers stay integers and precision is not
  lost; scientific notation is expanded to avoid exponent output).
  TODO(v1): number-format styles are ignored — date/time serials are emitted as
  their raw serial number, not converted to a calendar string.
- The grid is reconstructed from each cell's ``r="A1"`` reference so gaps become
  empty strings and every row is normalised to the sheet's column count (taken
  from the ``<dimension>`` hint and/or the widest observed cell).
- The first row becomes ``meta["headers"]``, the rest ``meta["rows"]`` — the same
  TABLE meta shape the Markdown parser produces.
- Empty sheets are skipped; a wholly empty workbook yields ``UniversalDoc()``.
- A non-ZIP payload or a corrupt archive raises :class:`ValueError`.
"""
from __future__ import annotations

import io
import posixpath
import zipfile
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree as ET

from src.engine.doc.models import Block, BlockType, Page, UniversalDoc

# ── namespaces ────────────────────────────────────────────────
_MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_PKG_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"

_WORKBOOK_PART = "xl/workbook.xml"
_WORKBOOK_RELS = "xl/_rels/workbook.xml.rels"
_SHARED_STRINGS = "xl/sharedStrings.xml"
_WORKBOOK_DIR = "xl"

_C = _MAIN + "c"
_V = _MAIN + "v"
_IS = _MAIN + "is"
_T = _MAIN + "t"
_ROW = _MAIN + "row"
_SHEET_DATA = _MAIN + "sheetData"
_DIMENSION = _MAIN + "dimension"


# ── column reference helpers ──────────────────────────────────

def _col_letters(ref: str) -> str:
    """Return the leading letter run of a cell reference (``AB12`` -> ``AB``)."""
    letters: list[str] = []
    for ch in ref:
        if ch.isalpha():
            letters.append(ch)
        else:
            break
    return "".join(letters)


def _col_index(ref: str) -> int:
    """Zero-based column index of a cell/column reference (``A`` -> 0, ``AA`` -> 26).

    Returns -1 when *ref* has no leading letters (malformed).
    """
    letters = _col_letters(ref)
    if not letters:
        return -1
    idx = 0
    for ch in letters:
        idx = idx * 26 + (ord(ch.upper()) - ord("A") + 1)
    return idx - 1


# ── number formatting ─────────────────────────────────────────

def _format_number(raw: str) -> str:
    """Stringify a numeric cell value, keeping integers integral and avoiding
    exponent notation.

    XLSX stores numbers in a canonical decimal form, so the verbatim ``<v>`` text
    is preserved as-is (this keeps integers integral and loses no precision).
    Only values written in scientific notation are expanded.
    """
    if "e" not in raw and "E" not in raw:
        return raw
    try:
        return format(Decimal(raw), "f")
    except InvalidOperation:
        return raw


# ── shared strings ────────────────────────────────────────────

def _build_shared_strings(xml: bytes | None) -> list[str]:
    """Materialise ``sharedStrings.xml`` into an index-addressable string list.

    Each ``<si>`` may hold a single ``<t>`` or several rich-text ``<r><t>`` runs;
    all descendant ``<t>`` text is concatenated (formatting is dropped in v1).
    """
    if not xml:
        return []
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return []
    strings: list[str] = []
    for si in root.findall(_MAIN + "si"):
        strings.append("".join(t.text or "" for t in si.iter(_T)))
    return strings


# ── workbook relationships ────────────────────────────────────

def _resolve_target(target: str) -> str:
    """Resolve a relationship ``Target`` to a package part path.

    Relative targets are resolved against the workbook's directory (``xl/``);
    a leading ``/`` marks a package-root-absolute target.
    """
    if target.startswith("/"):
        return posixpath.normpath(target.lstrip("/"))
    return posixpath.normpath(posixpath.join(_WORKBOOK_DIR, target))


def _build_rels(xml: bytes | None) -> dict[str, str]:
    """Map each relationship ``Id`` to its resolved part path."""
    rels: dict[str, str] = {}
    if not xml:
        return rels
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return rels
    for rel in root.findall(_PKG_REL + "Relationship"):
        rid = rel.get("Id")
        target = rel.get("Target")
        if rid and target:
            rels[rid] = _resolve_target(target)
    return rels


def _list_sheets(
    workbook_xml: bytes, rels: dict[str, str]
) -> list[tuple[str, str]]:
    """Return ``(sheet_name, part_path)`` pairs in workbook order.

    Falls back to the conventional ``xl/worksheets/sheetN.xml`` name when a
    sheet's ``r:id`` is not resolvable via the rels part.
    """
    root = ET.fromstring(workbook_xml)
    sheets_el = root.find(_MAIN + "sheets")
    if sheets_el is None:
        return []
    out: list[tuple[str, str]] = []
    for i, sheet in enumerate(sheets_el.findall(_MAIN + "sheet"), start=1):
        name = sheet.get("name") or f"Sheet{i}"
        rid = sheet.get(_REL + "id")
        path = rels.get(rid) if rid else None
        if path is None:
            path = f"xl/worksheets/sheet{i}.xml"
        out.append((name, path))
    return out


# ── worksheet -> matrix ───────────────────────────────────────

def _cell_value(cell: ET.Element, shared: list[str]) -> str:
    """Resolve a single ``<c>`` element to its display string."""
    t = cell.get("t")
    if t == "s":
        v = cell.find(_V)
        if v is None or v.text is None:
            return ""
        try:
            idx = int(v.text)
        except ValueError:
            return ""
        return shared[idx] if 0 <= idx < len(shared) else ""
    if t == "inlineStr":
        is_el = cell.find(_IS)
        if is_el is None:
            return ""
        return "".join(t.text or "" for t in is_el.iter(_T))
    if t == "b":
        v = cell.find(_V)
        return "TRUE" if (v is not None and v.text == "1") else "FALSE"
    if t in ("str", "e", "d"):
        v = cell.find(_V)
        return v.text if (v is not None and v.text is not None) else ""
    # number (t is None or "n"); formula-cached numbers land here too.
    v = cell.find(_V)
    if v is None or v.text is None:
        return ""
    return _format_number(v.text)


def _dimension_cols(root: ET.Element) -> int:
    """Column count implied by the ``<dimension ref="A1:H21">`` hint (0 if absent)."""
    dim = root.find(_DIMENSION)
    if dim is None:
        return 0
    ref = dim.get("ref") or ""
    end = ref.split(":")[-1]
    return _col_index(end) + 1 if end else 0


def _sheet_matrix(xml: bytes, shared: list[str]) -> list[list[str]]:
    """Reconstruct a rectangular string matrix from a worksheet part.

    Cell column positions are restored from each ``r`` reference (gaps -> ""),
    and every row is padded to the sheet's column count.
    """
    root = ET.fromstring(xml)
    sheet_data = root.find(_SHEET_DATA)
    if sheet_data is None:
        return []

    raw_rows: list[list[tuple[int, str]]] = []
    max_col = _dimension_cols(root) - 1
    for row in sheet_data.findall(_ROW):
        cells: list[tuple[int, str]] = []
        fallback_col = 0
        for cell in row.findall(_C):
            ref = cell.get("r")
            col = _col_index(ref) if ref else fallback_col
            if col < 0:
                col = fallback_col
            fallback_col = col + 1
            cells.append((col, _cell_value(cell, shared)))
            if col > max_col:
                max_col = col
        raw_rows.append(cells)

    if max_col < 0:
        return []

    width = max_col + 1
    matrix: list[list[str]] = []
    for cells in raw_rows:
        line = [""] * width
        for col, value in cells:
            if 0 <= col < width:
                line[col] = value
        matrix.append(line)
    return matrix


def _matrix_is_empty(matrix: list[list[str]]) -> bool:
    """True when the matrix has no rows, or every cell is the empty string."""
    return not any(any(cell for cell in row) for row in matrix)


def _table_block(matrix: list[list[str]]) -> Block:
    """Build a TABLE block (Markdown-compatible meta) from a non-empty matrix."""
    headers = matrix[0]
    rows = matrix[1:]
    return Block(
        type=BlockType.TABLE,
        content="",
        meta={"headers": headers, "rows": rows},
    )


# ── public API ────────────────────────────────────────────────

class XLSXParser:
    """Parse Excel .xlsx (OOXML SpreadsheetML) workbooks into a UniversalDoc."""

    def parse_bytes(self, content: bytes) -> UniversalDoc:
        try:
            archive = zipfile.ZipFile(io.BytesIO(content))
        except zipfile.BadZipFile as exc:
            # Non-ZIP payload: corrupt file or a legacy .xls / encrypted workbook.
            raise ValueError(f"Not a valid XLSX (ZIP) file: {exc}") from exc

        with archive:
            names = set(archive.namelist())
            if _WORKBOOK_PART not in names:
                raise ValueError("Missing xl/workbook.xml in XLSX")

            try:
                workbook_xml = archive.read(_WORKBOOK_PART)
                rels = _build_rels(
                    archive.read(_WORKBOOK_RELS)
                    if _WORKBOOK_RELS in names
                    else None
                )
                shared = _build_shared_strings(
                    archive.read(_SHARED_STRINGS)
                    if _SHARED_STRINGS in names
                    else None
                )
                sheets = _list_sheets(workbook_xml, rels)

                # (sheet_name, table_block) for every non-empty sheet, in order.
                emitted: list[tuple[str, Block]] = []
                for name, path in sheets:
                    if path not in names:
                        continue
                    matrix = _sheet_matrix(archive.read(path), shared)
                    if _matrix_is_empty(matrix):
                        continue
                    emitted.append((name, _table_block(matrix)))
            except ET.ParseError as exc:
                raise ValueError(f"Corrupt XLSX XML: {exc}") from exc

        if not emitted:
            return UniversalDoc()

        multi = len(emitted) > 1
        pages: list[Page] = []
        for name, table in emitted:
            blocks: list[Block] = []
            if multi:
                blocks.append(
                    Block(
                        type=BlockType.HEADING,
                        content=name,
                        meta={"level": 2},
                    )
                )
            blocks.append(table)
            pages.append(Page(blocks=blocks))

        return UniversalDoc(pages=pages)
