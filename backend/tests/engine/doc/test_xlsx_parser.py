"""Tests for the XLSX (OOXML SpreadsheetML) parser.

Two tiers:
- Synthetic in-memory .xlsx zips exercise each feature in isolation
  (shared/inline/number/bool/formula cells, empty-cell column alignment,
  multi-sheet headings, empty workbook, bad-input handling).
- Real reference workbooks in ``reference_data/xlsx`` are parsed end-to-end and
  asserted against measured strings (including Korean cells) and a timing bound
  on the ~855 KB administrative-code sheet; skipped when the files are absent.

All tests call ``XLSXParser.parse_bytes`` directly — ingest routing is the
coordinator's responsibility.
"""
from __future__ import annotations

import io
import time
import zipfile
from pathlib import Path

import pytest
from src.engine.doc.models import BlockType
from src.engine.doc.parsers.xlsx import XLSXParser

_REF_DIR = Path(__file__).resolve().parent / "reference_data" / "xlsx"
_MAIN = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
_R = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'


# ── synthetic .xlsx builders ──────────────────────────────────

def _make_xlsx(
    sheets: list[tuple[str, str]],
    shared: list[str] | None = None,
) -> bytes:
    """Build a minimal in-memory .xlsx (ZIP).

    *sheets* is a list of ``(sheet_name, sheetdata_inner_xml)`` where the inner
    XML is the contents of ``<sheetData>`` (a run of ``<row>`` elements).
    """
    sheet_entries = "".join(
        f'<sheet name="{name}" sheetId="{i}" r:id="rId{i}"/>'
        for i, (name, _) in enumerate(sheets, start=1)
    )
    workbook = (
        f"<workbook {_MAIN} {_R}><sheets>{sheet_entries}</sheets></workbook>"
    )
    rel_entries = "".join(
        f'<Relationship Id="rId{i}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/'
        'relationships/worksheet" '
        f'Target="worksheets/sheet{i}.xml"/>'
        for i in range(1, len(sheets) + 1)
    )
    rels = (
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/'
        f'2006/relationships">{rel_entries}</Relationships>'
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", rels)
        for i, (_, data) in enumerate(sheets, start=1):
            z.writestr(
                f"xl/worksheets/sheet{i}.xml",
                f"<worksheet {_MAIN}><sheetData>{data}</sheetData></worksheet>",
            )
        if shared is not None:
            si = "".join(f"<si><t>{s}</t></si>" for s in shared)
            z.writestr(
                "xl/sharedStrings.xml",
                f"<sst {_MAIN} count=\"{len(shared)}\" "
                f"uniqueCount=\"{len(shared)}\">{si}</sst>",
            )
    return buf.getvalue()


def _cell(ref: str, value: str = "", t: str | None = None) -> str:
    attr = f' t="{t}"' if t else ""
    if t == "inlineStr":
        return f'<c r="{ref}"{attr}><is><t>{value}</t></is></c>'
    if value == "" and t is None:
        return f'<c r="{ref}"/>'
    return f'<c r="{ref}"{attr}><v>{value}</v></c>'


def _row(ref: str, cells: str) -> str:
    return f'<row r="{ref}">{cells}</row>'


def _parse(sheets, shared=None):
    return XLSXParser().parse_bytes(_make_xlsx(sheets, shared))


# ── synthetic: cell types & alignment ─────────────────────────

def test_shared_inline_and_number_cells():
    shared = ["name", "alice"]
    data = (
        _row("1", _cell("A1", "0", "s") + _cell("B1", "Age", "inlineStr"))
        + _row("2", _cell("A2", "1", "s") + _cell("B2", "42"))
    )
    doc = _parse([("Data", data)], shared)
    assert len(doc.pages) == 1
    block = doc.pages[0].blocks[0]
    assert block.type is BlockType.TABLE
    assert block.meta["headers"] == ["name", "Age"]
    assert block.meta["rows"] == [["alice", "42"]]


def test_empty_cell_column_alignment():
    # Row 2 omits column B entirely; the gap must become "" at index 1.
    data = (
        _row("1", _cell("A1", "h1", "inlineStr") + _cell(
            "B1", "h2", "inlineStr") + _cell("C1", "h3", "inlineStr"))
        + _row("2", _cell("A2", "x", "inlineStr") + _cell("C2", "z", "inlineStr"))
    )
    doc = _parse([("S", data)])
    rows = doc.pages[0].blocks[0].meta["rows"]
    assert rows == [["x", "", "z"]]


def test_integer_number_stays_integral():
    data = (
        _row("1", _cell("A1", "n", "inlineStr"))
        + _row("2", _cell("A2", "1000000000000"))
        + _row("3", _cell("A3", "3.14"))
    )
    rows = _parse([("S", data)]).pages[0].blocks[0].meta["rows"]
    assert rows == [["1000000000000"], ["3.14"]]


def test_scientific_notation_expanded():
    data = _row("1", _cell("A1", "h", "inlineStr")) + _row(
        "2", _cell("A2", "1E+21")
    )
    rows = _parse([("S", data)]).pages[0].blocks[0].meta["rows"]
    assert rows == [["1000000000000000000000"]]


def test_bool_and_formula_cells():
    # t="b" -> TRUE/FALSE; a formula's cached <v> is used verbatim.
    data = (
        _row("1", _cell("A1", "flag", "inlineStr") + _cell(
            "B1", "calc", "inlineStr"))
        + _row(
            "2",
            _cell("A2", "1", "b")
            + '<c r="B2"><f>1+1</f><v>2</v></c>',
        )
    )
    rows = _parse([("S", data)]).pages[0].blocks[0].meta["rows"]
    assert rows == [["TRUE", "2"]]


# ── synthetic: sheet -> page mapping ──────────────────────────

def test_single_sheet_omits_heading():
    data = _row("1", _cell("A1", "h", "inlineStr")) + _row(
        "2", _cell("A2", "v", "inlineStr")
    )
    doc = _parse([("Only", data)])
    assert len(doc.pages) == 1
    assert [b.type for b in doc.pages[0].blocks] == [BlockType.TABLE]


def test_multi_sheet_inserts_heading():
    data = _row("1", _cell("A1", "h", "inlineStr")) + _row(
        "2", _cell("A2", "v", "inlineStr")
    )
    doc = _parse([("First", data), ("Second", data)])
    assert len(doc.pages) == 2
    p0 = doc.pages[0]
    assert p0.blocks[0].type is BlockType.HEADING
    assert p0.blocks[0].content == "First"
    assert p0.blocks[0].meta == {"level": 2}
    assert p0.blocks[1].type is BlockType.TABLE
    assert doc.pages[1].blocks[0].content == "Second"


def test_empty_sheets_are_skipped():
    full = _row("1", _cell("A1", "h", "inlineStr")) + _row(
        "2", _cell("A2", "v", "inlineStr")
    )
    doc = _parse([("Blank", ""), ("Real", full)])
    # Only the non-empty sheet becomes a page -> single page -> no heading.
    assert len(doc.pages) == 1
    assert [b.type for b in doc.pages[0].blocks] == [BlockType.TABLE]


def test_wholly_empty_workbook():
    doc = _parse([("A", ""), ("B", "")])
    assert doc.pages == []


# ── synthetic: bad input ──────────────────────────────────────

def test_non_zip_raises_value_error():
    with pytest.raises(ValueError):
        XLSXParser().parse_bytes(b"this is not a zip file at all")


def test_missing_workbook_raises_value_error():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("junk.txt", "nope")
    with pytest.raises(ValueError):
        XLSXParser().parse_bytes(buf.getvalue())


# ── real reference workbooks (measured) ───────────────────────

def _load(name: str) -> bytes:
    return (_REF_DIR / name).read_bytes()


_HAS_BITCOIN = (_REF_DIR / "bitcoin_10_years_data.xlsx").exists()
_HAS_KIK = (_REF_DIR / "KIKmix.20250513.xlsx").exists()
_HAS_GANTT = (_REF_DIR / "예쁜_간트차트_2025.xlsx").exists()


@pytest.mark.skipif(not _HAS_BITCOIN, reason="bitcoin reference file absent")
def test_real_bitcoin():
    doc = XLSXParser().parse_bytes(_load("bitcoin_10_years_data.xlsx"))
    assert len(doc.pages) == 1
    table = doc.pages[0].blocks[0]
    assert table.type is BlockType.TABLE
    assert table.meta["headers"] == ["timestamp", "price"]
    assert len(table.meta["rows"]) == 3651
    assert table.meta["rows"][0] == ["41809.41770992755", "0"]
    assert table.meta["rows"][1] == ["41810.41770992755", "10"]


@pytest.mark.skipif(not _HAS_KIK, reason="KIKmix reference file absent")
def test_real_kikmix_headers_and_korean_cells():
    doc = XLSXParser().parse_bytes(_load("KIKmix.20250513.xlsx"))
    assert len(doc.pages) == 1
    table = doc.pages[0].blocks[0]
    assert table.meta["headers"] == [
        "행정동코드", "시도명", "시군구명", "읍면동명",
        "법정동코드", "동리명", "생성일자", "말소일자",
    ]
    rows = table.meta["rows"]
    assert len(rows) == 21808
    # Row 2 in the sheet omits 시군구명/읍면동명/말소일자 -> "" gaps.
    assert rows[0] == [
        "1100000000", "서울특별시", "", "",
        "1100000000", "서울특별시", "19880423", "",
    ]
    assert rows[1] == [
        "1111000000", "서울특별시", "종로구", "",
        "1111000000", "종로구", "19880423", "",
    ]


@pytest.mark.skipif(not _HAS_KIK, reason="KIKmix reference file absent")
def test_real_kikmix_performance():
    payload = _load("KIKmix.20250513.xlsx")
    start = time.perf_counter()
    doc = XLSXParser().parse_bytes(payload)
    elapsed = time.perf_counter() - start
    assert len(doc.pages) == 1
    # ~855 KB / 21.8k rows must parse well within a few seconds.
    assert elapsed < 5.0, f"KIKmix parse took {elapsed:.2f}s"


@pytest.mark.skipif(not _HAS_GANTT, reason="gantt reference file absent")
def test_real_gantt_inline_strings():
    doc = XLSXParser().parse_bytes(_load("예쁜_간트차트_2025.xlsx"))
    assert len(doc.pages) == 1
    table = doc.pages[0].blocks[0]
    headers = table.meta["headers"]
    assert len(headers) == 15  # A:O
    assert headers[0] == ""
    assert headers[1] == "3.21 이전"
    assert headers[2] == "3.27"
    rows = table.meta["rows"]
    assert len(rows) == 6
    assert rows[0][0] == "기획 및 설계"
    assert rows[1][2] == "MVP 구현 (iOS)"
