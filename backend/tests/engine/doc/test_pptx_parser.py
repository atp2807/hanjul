"""Tests for the PPTX (OOXML) parser.

Real-fixture assertions use *measured* values taken directly from the sample
decks in ``reference_data/pptx/`` (see the module docstring of each helper), so
they guard against silent regressions rather than invented expectations.
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest
from src.engine.doc.models import BlockType
from src.engine.doc.parsers.pptx import PPTXParser

_FIXTURE_DIR = Path(__file__).resolve().parent / "reference_data" / "pptx"

_SSAKSSEURI = _FIXTURE_DIR / "[기획] 싹쓰리 Admin.pptx"
_OSAN = _FIXTURE_DIR / "오산대학교 OFFICE365 계정 생성 방법.pptx"
_PRODUCT = _FIXTURE_DIR / "제품소개.pptx"


def _parse(path: Path):
    return PPTXParser().parse_bytes(path.read_bytes())


def _all_text(page) -> str:
    return "\n".join(b.content for b in page.blocks)


# ── real fixtures ─────────────────────────────────────────────

@pytest.mark.skipif(not _SSAKSSEURI.exists(), reason="fixture missing")
def test_ssaksseuri_slide_count_and_title_heading():
    doc = _parse(_SSAKSSEURI)
    # sldIdLst declares 32 slides (measured from ppt/presentation.xml).
    assert len(doc.pages) == 32

    # slide1 title placeholder -> level-1 HEADING with measured text.
    headings = [b for b in doc.pages[0].blocks if b.type is BlockType.HEADING]
    assert headings, "expected a title heading on slide 1"
    # The title is authored across three lines (three a:p paragraphs); the
    # heading preserves the breaks as newlines (measured).
    assert headings[0].content == "2024~\n싹쓰리 Admin\n변경점 정리"
    assert headings[0].meta.get("level") == 1


@pytest.mark.skipif(not _SSAKSSEURI.exists(), reason="fixture missing")
def test_ssaksseuri_table_extraction():
    doc = _parse(_SSAKSSEURI)
    # slide6 (index 5) carries a 7-column table with a measured header row.
    tables = [b for b in doc.pages[5].blocks if b.type is BlockType.TABLE]
    assert tables, "expected a table on slide 6"
    tbl = tables[0]
    assert tbl.meta["col_count"] == 7
    assert tbl.meta["row_count"] == 4
    header = tbl.meta["rows"][0]
    assert header == [
        "구분", "예상세액 발송일시", "국세", "지방세",
        "신고수수료", "계산방법", "신고계정",
    ]
    # a data cell text is preserved
    assert "2024-05-18 21:04:05" in tbl.content


@pytest.mark.skipif(not _OSAN.exists(), reason="fixture missing")
def test_osan_slides_and_paragraph_text():
    doc = _parse(_OSAN)
    # sldIdLst declares 3 slides (measured).
    assert len(doc.pages) == 3
    # slide1 has no title placeholder — its text is plain PARAGRAPH blocks.
    text = _all_text(doc.pages[0])
    assert "오산대학교 포탈 로그인" in text
    assert any(b.type is BlockType.PARAGRAPH for b in doc.pages[0].blocks)
    # slide size 12192000 x 6858000 EMU -> 338.7 x 190.5 mm.
    layout = doc.metadata.get("page_layout")
    assert layout == {"width_mm": 338.7, "height_mm": 190.5}


@pytest.mark.skipif(not _PRODUCT.exists(), reason="fixture missing")
def test_product_slide_count_and_title():
    doc = _parse(_PRODUCT)
    # sldIdLst declares 7 slides (measured).
    assert len(doc.pages) == 7
    # slide1 ctrTitle placeholder -> level-1 HEADING (measured text).
    headings = [b for b in doc.pages[0].blocks if b.type is BlockType.HEADING]
    # ctrTitle authored across lines -> newline-joined heading (measured).
    assert headings[0].content == "제품소개\n\n-BATCH PLANTS"
    assert headings[0].meta.get("level") == 1
    # media images are surfaced by basename.
    assert doc.metadata.get("images")
    assert all("/" not in name for name in doc.metadata["images"])


@pytest.mark.skipif(not _PRODUCT.exists(), reason="fixture missing")
def test_product_slide_order_matches_sldidlst():
    # 제품소개 sldIdLst order maps rId2..rId8 -> slide1..slide7 in sequence;
    # every page must carry at least one block (no dropped/misordered slides).
    doc = _parse(_PRODUCT)
    assert all(page.blocks for page in doc.pages)


# ── synthetic fixtures ────────────────────────────────────────

def _make_pptx(slides: list[str], *, slide_size: bool = True) -> bytes:
    """Build a minimal valid .pptx from raw slide XML bodies.

    ``slides`` are ordered spTree XML fragments; relationships and sldIdLst are
    generated so slide *N* is ``rId{N}`` in declared order.
    """
    buf = io.BytesIO()
    ns = (
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'
    )
    sld_ids = "".join(
        f'<p:sldId id="{256 + i}" r:id="rId{i + 1}"/>' for i in range(len(slides))
    )
    sz = '<p:sldSz cx="9144000" cy="6858000"/>' if slide_size else ""
    presentation = (
        f'<p:presentation {ns}><p:sldIdLst>{sld_ids}</p:sldIdLst>{sz}'
        f"</p:presentation>"
    )
    rels = (
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + "".join(
            f'<Relationship Id="rId{i + 1}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" '
            f'Target="slides/slide{i + 1}.xml"/>'
            for i in range(len(slides))
        )
        + "</Relationships>"
    )
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("ppt/presentation.xml", presentation)
        z.writestr("ppt/_rels/presentation.xml.rels", rels)
        for i, body in enumerate(slides):
            z.writestr(
                f"ppt/slides/slide{i + 1}.xml",
                f"<p:sld {ns}><p:cSld><p:spTree>{body}</p:spTree></p:cSld></p:sld>",
            )
    return buf.getvalue()


def _title_sp(text: str) -> str:
    return (
        '<p:sp><p:nvSpPr><p:cNvPr id="1" name="Title"/><p:cNvSpPr/>'
        '<p:nvPr><p:ph type="title"/></p:nvPr></p:nvSpPr>'
        f'<p:txBody><a:p><a:r><a:t>{text}</a:t></a:r></a:p></p:txBody></p:sp>'
    )


def _body_sp(text: str) -> str:
    return (
        '<p:sp><p:nvSpPr><p:cNvPr id="2" name="Body"/><p:cNvSpPr/>'
        "<p:nvPr/></p:nvSpPr>"
        f'<p:txBody><a:p><a:r><a:t>{text}</a:t></a:r></a:p></p:txBody></p:sp>'
    )


def test_synthetic_minimal_slides():
    data = _make_pptx([_title_sp("Hello") + _body_sp("World"), _body_sp("Second")])
    doc = PPTXParser().parse_bytes(data)
    assert len(doc.pages) == 2

    heads = [b for b in doc.pages[0].blocks if b.type is BlockType.HEADING]
    paras = [b for b in doc.pages[0].blocks if b.type is BlockType.PARAGRAPH]
    assert heads[0].content == "Hello"
    assert heads[0].meta["level"] == 1
    assert paras[0].content == "World"

    assert doc.pages[1].blocks[0].content == "Second"
    # sldSz 9144000 x 6858000 EMU -> 254.0 x 190.5 mm.
    assert doc.metadata["page_layout"] == {"width_mm": 254.0, "height_mm": 190.5}


def test_synthetic_table():
    tbl_xml = (
        "<p:graphicFrame><a:graphic><a:graphicData><a:tbl>"
        "<a:tr><a:tc><a:txBody><a:p><a:r><a:t>H1</a:t></a:r></a:p></a:txBody></a:tc>"
        "<a:tc><a:txBody><a:p><a:r><a:t>H2</a:t></a:r></a:p></a:txBody></a:tc></a:tr>"
        "<a:tr><a:tc><a:txBody><a:p><a:r><a:t>a</a:t></a:r></a:p></a:txBody></a:tc>"
        "<a:tc><a:txBody><a:p><a:r><a:t>b</a:t></a:r></a:p></a:txBody></a:tc></a:tr>"
        "</a:tbl></a:graphicData></a:graphic></p:graphicFrame>"
    )
    doc = PPTXParser().parse_bytes(_make_pptx([tbl_xml]))
    tables = [b for b in doc.pages[0].blocks if b.type is BlockType.TABLE]
    assert len(tables) == 1
    tbl = tables[0]
    assert tbl.meta["col_count"] == 2
    assert tbl.meta["row_count"] == 2
    assert tbl.meta["rows"] == [["H1", "H2"], ["a", "b"]]
    assert tbl.content == "H1 | H2\na | b"


def test_synthetic_table_with_gridspan():
    # First row: one cell spanning 2 columns (gridSpan=2 + an hMerge continuation).
    tbl_xml = (
        "<p:graphicFrame><a:graphic><a:graphicData><a:tbl>"
        '<a:tr><a:tc gridSpan="2"><a:txBody><a:p><a:r><a:t>Merged</a:t></a:r></a:p>'
        '</a:txBody></a:tc><a:tc hMerge="1"><a:txBody><a:p/></a:txBody></a:tc></a:tr>'
        "<a:tr><a:tc><a:txBody><a:p><a:r><a:t>a</a:t></a:r></a:p></a:txBody></a:tc>"
        "<a:tc><a:txBody><a:p><a:r><a:t>b</a:t></a:r></a:p></a:txBody></a:tc></a:tr>"
        "</a:tbl></a:graphicData></a:graphic></p:graphicFrame>"
    )
    doc = PPTXParser().parse_bytes(_make_pptx([tbl_xml]))
    tbl = doc.pages[0].blocks[0]
    assert tbl.meta["col_count"] == 2
    origin = tbl.meta["cells"][0]
    assert origin["text"] == "Merged"
    assert origin["colspan"] == 2
    assert origin["row"] == 0 and origin["col"] == 0


def test_non_zip_raises_value_error():
    with pytest.raises(ValueError):
        PPTXParser().parse_bytes(b"this is not a zip file")


def test_missing_presentation_raises_value_error():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("random.txt", "nope")
    with pytest.raises(ValueError):
        PPTXParser().parse_bytes(buf.getvalue())
