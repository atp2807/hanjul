"""Tests for the DOCX (OOXML) parser.

Two tiers:
- Synthetic in-memory .docx zips exercise each feature in isolation
  (heading resolution, run formatting -> strong/em/u, gridSpan/vMerge tables,
  numPr lists, media listing, bad-input handling).
- Real reference documents in ``reference_data/docx`` are parsed end-to-end and
  asserted against measured strings; skipped when the files are absent.

All tests call ``DOCXParser.parse_bytes`` directly — ingest routing is the
coordinator's responsibility.
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest
from src.engine.doc.models import BlockType
from src.engine.doc.parsers.docx import DOCXParser

_REF_DIR = Path(__file__).resolve().parent / "reference_data" / "docx"

# OOXML namespace declaration shared by every synthetic body.
_NS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


# ── synthetic .docx builders ──────────────────────────────────

def _make_docx(
    body_xml: str,
    styles_xml: str | None = None,
    media: list[str] | None = None,
) -> bytes:
    """Build a minimal in-memory .docx (ZIP) with the given body XML."""
    document = f'<w:document {_NS}><w:body>{body_xml}</w:body></w:document>'
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("word/document.xml", document)
        if styles_xml is not None:
            z.writestr("word/styles.xml", f'<w:styles {_NS}>{styles_xml}</w:styles>')
        for name in media or []:
            z.writestr(f"word/media/{name}", b"\x00binary")
    return buf.getvalue()


def _p(runs: str, ppr: str = "") -> str:
    return f"<w:p>{ppr}{runs}</w:p>"


def _run(text: str, rpr: str = "") -> str:
    return f'<w:r>{rpr}<w:t xml:space="preserve">{text}</w:t></w:r>'


def _parse(body_xml: str, **kw):
    return DOCXParser().parse_bytes(_make_docx(body_xml, **kw))


# ── synthetic: paragraphs & headings ──────────────────────────

def test_single_page_flow():
    doc = _parse(_p(_run("hello")))
    assert len(doc.pages) == 1
    assert [b.type for b in doc.pages[0].blocks] == [BlockType.PARAGRAPH]
    assert doc.pages[0].blocks[0].content == "hello"


def test_heading_via_pstyle_name_resolution():
    # Localized styleId "1" resolves through styles.xml to "heading 1".
    body = _p(_run("Title"), ppr='<w:pPr><w:pStyle w:val="1"/></w:pPr>')
    styles = '<w:style w:styleId="1"><w:name w:val="heading 1"/></w:style>'
    block = _parse(body, styles_xml=styles).pages[0].blocks[0]
    assert block.type == BlockType.HEADING
    assert block.meta["level"] == 1
    assert block.content == "Title"


def test_heading_level_from_styleid_fallback():
    # No styles.xml: the styleId itself ("Heading3") carries the level.
    body = _p(_run("Sub"), ppr='<w:pPr><w:pStyle w:val="Heading3"/></w:pPr>')
    block = _parse(body).pages[0].blocks[0]
    assert block.type == BlockType.HEADING
    assert block.meta["level"] == 3


def test_header_style_is_not_a_heading():
    # A "header" style (page header) must not be mistaken for a heading.
    body = _p(_run("pagehdr"), ppr='<w:pPr><w:pStyle w:val="a5"/></w:pPr>')
    styles = '<w:style w:styleId="a5"><w:name w:val="header"/></w:style>'
    block = _parse(body, styles_xml=styles).pages[0].blocks[0]
    assert block.type == BlockType.PARAGRAPH


# ── synthetic: run inline formatting ──────────────────────────

def test_bold_run_becomes_strong():
    block = _parse(_p(_run("bold", rpr="<w:rPr><w:b/></w:rPr>"))).pages[0].blocks[0]
    assert block.content == "<strong>bold</strong>"


def test_italic_run_becomes_em():
    block = _parse(_p(_run("it", rpr="<w:rPr><w:i/></w:rPr>"))).pages[0].blocks[0]
    assert block.content == "<em>it</em>"


def test_underline_run_becomes_u():
    rpr = '<w:rPr><w:u w:val="single"/></w:rPr>'
    block = _parse(_p(_run("under", rpr=rpr))).pages[0].blocks[0]
    assert block.content == "<u>under</u>"


def test_bold_italic_nesting():
    rpr = "<w:rPr><w:b/><w:i/></w:rPr>"
    block = _parse(_p(_run("bi", rpr=rpr))).pages[0].blocks[0]
    assert block.content == "<strong><em>bi</em></strong>"


def test_toggle_off_bold_is_plain():
    rpr = '<w:rPr><w:b w:val="false"/></w:rPr>'
    block = _parse(_p(_run("plain", rpr=rpr))).pages[0].blocks[0]
    assert block.content == "plain"


def test_run_text_is_escaped():
    block = _parse(_p(_run("a &lt; b &amp; c"))).pages[0].blocks[0]
    # The literal "<" character in the source must survive as an entity.
    assert "&lt;" in block.content and "<b" not in block.content


# ── synthetic: lists ──────────────────────────────────────────

def test_consecutive_numpr_paragraphs_collapse_to_one_list():
    numpr = "<w:pPr><w:numPr><w:ilvl w:val=\"0\"/><w:numId w:val=\"1\"/></w:numPr></w:pPr>"
    body = _p(_run("one"), ppr=numpr) + _p(_run("two"), ppr=numpr) + _p(_run("after"))
    blocks = _parse(body).pages[0].blocks
    assert [b.type for b in blocks] == [BlockType.LIST, BlockType.PARAGRAPH]
    assert blocks[0].content == "one\ntwo"
    assert blocks[0].meta["ordered"] is False  # v1: numbering.xml not read


def test_heading_with_numpr_stays_heading():
    numpr = "<w:numPr><w:ilvl w:val=\"0\"/><w:numId w:val=\"1\"/></w:numPr>"
    ppr = f'<w:pPr><w:pStyle w:val="Heading2"/>{numpr}</w:pPr>'
    block = _parse(_p(_run("H"), ppr=ppr)).pages[0].blocks[0]
    assert block.type == BlockType.HEADING and block.meta["level"] == 2


# ── synthetic: tables ─────────────────────────────────────────

def _tc(text: str, tcpr: str = "") -> str:
    return f"<w:tc>{tcpr}{_p(_run(text))}</w:tc>"


def test_simple_table():
    row1 = "<w:tr>" + _tc("a") + _tc("b") + "</w:tr>"
    row2 = "<w:tr>" + _tc("c") + _tc("d") + "</w:tr>"
    block = _parse(f"<w:tbl>{row1}{row2}</w:tbl>").pages[0].blocks[0]
    assert block.type == BlockType.TABLE
    assert block.meta["row_count"] == 2 and block.meta["col_count"] == 2
    texts = {(c["row"], c["col"]): c["text"] for c in block.meta["cells"]}
    assert texts == {(0, 0): "a", (0, 1): "b", (1, 0): "c", (1, 1): "d"}


def test_table_gridspan_colspan():
    span = '<w:tcPr><w:gridSpan w:val="2"/></w:tcPr>'
    row1 = "<w:tr>" + _tc("wide", span) + "</w:tr>"
    row2 = "<w:tr>" + _tc("l") + _tc("r") + "</w:tr>"
    block = _parse(f"<w:tbl>{row1}{row2}</w:tbl>").pages[0].blocks[0]
    assert block.meta["col_count"] == 2
    wide = next(c for c in block.meta["cells"] if c["text"] == "wide")
    assert wide["colspan"] == 2 and wide["col"] == 0
    right = next(c for c in block.meta["cells"] if c["text"] == "r")
    assert right["col"] == 1


def test_table_vmerge_rowspan():
    restart = '<w:tcPr><w:vMerge w:val="restart"/></w:tcPr>'
    cont = "<w:tcPr><w:vMerge/></w:tcPr>"
    row1 = "<w:tr>" + _tc("merged", restart) + _tc("x") + "</w:tr>"
    row2 = "<w:tr>" + _tc("", cont) + _tc("y") + "</w:tr>"
    block = _parse(f"<w:tbl>{row1}{row2}</w:tbl>").pages[0].blocks[0]
    assert block.meta["row_count"] == 2
    merged = next(c for c in block.meta["cells"] if c["text"] == "merged")
    assert merged["rowspan"] == 2
    # The continuation cell must not be emitted as its own cell.
    assert not any(c["row"] == 1 and c["col"] == 0 for c in block.meta["cells"])


# ── synthetic: media & bad input ──────────────────────────────

def test_media_listed_in_metadata():
    doc = DOCXParser().parse_bytes(
        _make_docx(_p(_run("x")), media=["image1.png", "image2.jpeg"])
    )
    assert doc.metadata["images"] == ["image1.png", "image2.jpeg"]


def test_non_zip_bytes_raises_valueerror():
    with pytest.raises(ValueError):
        DOCXParser().parse_bytes(b"this is not a zip file at all")


def test_missing_document_xml_raises_valueerror():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/styles.xml", "<x/>")
    with pytest.raises(ValueError):
        DOCXParser().parse_bytes(buf.getvalue())


def test_empty_paragraph_is_dropped():
    doc = _parse(_p("") + _p(_run("kept")))
    assert [b.content for b in doc.pages[0].blocks] == ["kept"]


# ── real reference documents ──────────────────────────────────

def _ref(name: str) -> Path:
    return _REF_DIR / name

_SHINGO = "신고유형 정리.docx"
_BEOPJEONG = "기술문서_행정안전부_행정표준코드_법정동코드.docx"
_JONGHAP = "1. To_Be_변환파일_수록형식_종합소득세[20260406]_최종_1차.docx"


@pytest.mark.skipif(not _ref(_SHINGO).exists(), reason="reference doc missing")
def test_real_shingo_paragraph_and_table():
    doc = DOCXParser().parse_bytes(_ref(_SHINGO).read_bytes())
    blocks = doc.pages[0].blocks
    assert blocks[0].type == BlockType.PARAGRAPH
    assert blocks[0].content.startswith("2026년 5월 종합소득세 신고를 앞두고")
    table = next(b for b in blocks if b.type == BlockType.TABLE)
    assert table.meta["row_count"] == 5 and table.meta["col_count"] == 3
    row0 = [c["text"] for c in table.meta["cells"] if c["row"] == 0]
    assert row0 == ["유형", "대상자 특징", "신고 방법 및 주의사항"]
    cell_1_0 = next(
        c["text"] for c in table.meta["cells"] if c["row"] == 1 and c["col"] == 0
    )
    assert cell_1_0 == "S 유형"


@pytest.mark.skipif(not _ref(_BEOPJEONG).exists(), reason="reference doc missing")
def test_real_beopjeong_headings_and_vmerge_table():
    doc = DOCXParser().parse_bytes(_ref(_BEOPJEONG).read_bytes())
    blocks = doc.pages[0].blocks
    headings = [b for b in blocks if b.type == BlockType.HEADING]
    assert (headings[0].meta["level"], headings[0].content) == (1, "1. 서비스 명세")
    assert (headings[1].meta["level"], headings[1].content) == (
        2,
        "1.1 공공데이터 API 서비스",
    )
    # Images are listed in metadata.
    assert doc.metadata["images"] == ["image1.png", "image2.png", "image3.png", "image4.png"]
    # First table carries real vMerge rowspans and gridSpan colspans.
    table = next(b for b in blocks if b.type == BlockType.TABLE)
    assert any(c["rowspan"] > 1 for c in table.meta["cells"])
    assert any(c["colspan"] > 1 for c in table.meta["cells"])
    assert table.meta["cells"][0]["text"] == "API 서비스 정보"


@pytest.mark.skipif(not _ref(_JONGHAP).exists(), reason="reference doc missing")
def test_real_jonghap_parses_with_tables_and_image():
    doc = DOCXParser().parse_bytes(_ref(_JONGHAP).read_bytes())
    blocks = doc.pages[0].blocks
    assert any(b.type == BlockType.TABLE for b in blocks)
    assert any(b.type == BlockType.PARAGRAPH for b in blocks)
    assert doc.metadata["images"] == ["image1.jpeg"]
