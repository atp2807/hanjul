"""Tests for HWP 5.x parser."""
from __future__ import annotations

from pathlib import Path

import pytest

REFERENCE_HWP = Path(__file__).resolve().parent / "reference_data" / "hwp" / "복무상황신고서_2512_박연미.hwp"


# ── Protocol conformance ──────────────────────────────────────


class TestHWPProtocol:
    def test_implements_binary_parser(self):
        from src.engine.doc.parsers.base import BinaryParser
        from src.engine.doc.parsers.hwp import HWPParser

        assert isinstance(HWPParser(), BinaryParser)

    def test_has_parse_bytes_method(self):
        from src.engine.doc.parsers.hwp import HWPParser

        parser = HWPParser()
        assert callable(getattr(parser, "parse_bytes", None))


# ── Edge cases ─────────────────────────────────────────────────


class TestHWPEdgeCases:
    def test_empty_bytes_raises(self):
        from src.engine.doc.parsers.hwp import HWPParser

        with pytest.raises(ValueError):
            HWPParser().parse_bytes(b"")

    def test_invalid_signature_raises(self):
        from src.engine.doc.parsers.hwp import HWPParser

        with pytest.raises(ValueError):
            HWPParser().parse_bytes(b"\x00" * 1024)


# ── Reference file parsing ─────────────────────────────────────


@pytest.mark.skipif(not REFERENCE_HWP.exists(), reason="reference HWP not available")
class TestHWPReferenceFile:
    @pytest.fixture(scope="class")
    def doc(self):
        from src.engine.doc.parsers.hwp import HWPParser

        return HWPParser().parse_bytes(REFERENCE_HWP.read_bytes())

    def test_returns_universal_doc(self, doc):
        from src.engine.doc.models import UniversalDoc

        assert isinstance(doc, UniversalDoc)

    def test_has_one_page(self, doc):
        assert len(doc.pages) == 1

    def test_has_blocks(self, doc):
        assert len(doc.pages[0].blocks) > 0

    # ── Text extraction ────────────────────────────────────────

    def test_contains_title(self, doc):
        texts = [b.content for b in doc.pages[0].blocks]
        assert any("복무상황 신고서" in t for t in texts)

    def test_contains_attachment_label(self, doc):
        texts = [b.content for b in doc.pages[0].blocks]
        assert any("붙임 3" in t for t in texts)

    def test_contains_name(self, doc):
        all_text = " ".join(b.content for b in doc.pages[0].blocks)
        assert "박연미" in all_text

    def test_contains_department(self, doc):
        all_text = " ".join(b.content for b in doc.pages[0].blocks)
        assert "ICT운영처" in all_text

    def test_contains_leave_type(self, doc):
        all_text = " ".join(b.content for b in doc.pages[0].blocks)
        assert "벤처창업휴직" in all_text

    # ── Block types ────────────────────────────────────────────

    def test_has_paragraph_blocks(self, doc):
        from src.engine.doc.models import BlockType

        types = {b.type for b in doc.pages[0].blocks}
        assert BlockType.PARAGRAPH in types

    def test_has_table_block(self, doc):
        from src.engine.doc.models import BlockType

        types = {b.type for b in doc.pages[0].blocks}
        assert BlockType.TABLE in types

    def test_table_has_row_col_meta(self, doc):
        from src.engine.doc.models import BlockType

        tables = [b for b in doc.pages[0].blocks if b.type == BlockType.TABLE]
        assert len(tables) >= 1
        assert "rows" in tables[0].meta
        assert isinstance(tables[0].meta["rows"], list)
        assert "headers" in tables[0].meta

    # ── Image detection ────────────────────────────────────────

    def test_images_in_metadata(self, doc):
        assert "images" in doc.metadata
        assert "BIN0001.png" in doc.metadata["images"]

    # ── Style extraction ──────────────────────────────────────

    def test_paragraph_has_style(self, doc):
        styled = [b for b in doc.pages[0].blocks if b.meta.get("style")]
        assert len(styled) > 0, "At least one paragraph should have style info"

    def test_style_has_font(self, doc):
        styled = [b for b in doc.pages[0].blocks if b.meta.get("style")]
        fonts = [b.meta["style"].get("font") for b in styled if b.meta["style"].get("font")]
        assert len(fonts) > 0, "At least one paragraph should have a font name"

    def test_style_has_size(self, doc):
        styled = [b for b in doc.pages[0].blocks if b.meta.get("style")]
        sizes = [b.meta["style"].get("size") for b in styled if b.meta["style"].get("size")]
        assert len(sizes) > 0
        assert all(isinstance(s, int | float) and s > 0 for s in sizes)

    def test_style_has_align(self, doc):
        styled = [b for b in doc.pages[0].blocks if b.meta.get("style")]
        aligns = {b.meta["style"].get("align") for b in styled if b.meta["style"].get("align")}
        assert len(aligns) > 0
        assert aligns <= {"left", "right", "center", "justify"}

    def test_style_has_color(self, doc):
        styled = [b for b in doc.pages[0].blocks if b.meta.get("style")]
        colors = [b.meta["style"].get("color") for b in styled if b.meta["style"].get("color")]
        assert len(colors) > 0
        assert all(c.startswith("#") and len(c) == 7 for c in colors)

    def test_style_bold_is_bool(self, doc):
        styled = [b for b in doc.pages[0].blocks if b.meta.get("style")]
        for b in styled:
            if "bold" in b.meta["style"]:
                assert isinstance(b.meta["style"]["bold"], bool)

    # ── Table cell structure ──────────────────────────────────

    def test_table_has_cells(self, doc):
        from src.engine.doc.models import BlockType

        tables = [b for b in doc.pages[0].blocks if b.type == BlockType.TABLE]
        assert len(tables) >= 1
        assert "cells" in tables[0].meta
        assert isinstance(tables[0].meta["cells"], list)
        assert len(tables[0].meta["cells"]) > 0

    def test_table_cell_has_position(self, doc):
        from src.engine.doc.models import BlockType

        table = [b for b in doc.pages[0].blocks if b.type == BlockType.TABLE][0]
        cell = table.meta["cells"][0]
        assert "col" in cell
        assert "row" in cell

    def test_table_cell_has_dimensions(self, doc):
        from src.engine.doc.models import BlockType

        table = [b for b in doc.pages[0].blocks if b.type == BlockType.TABLE][0]
        cell = table.meta["cells"][0]
        assert "width_mm" in cell
        assert "height_mm" in cell
        assert cell["width_mm"] > 0
        assert cell["height_mm"] > 0

    def test_table_has_col_row_count(self, doc):
        from src.engine.doc.models import BlockType

        table = [b for b in doc.pages[0].blocks if b.type == BlockType.TABLE][0]
        assert table.meta["col_count"] > 0
        assert table.meta["row_count"] > 0

    def test_table_cell_has_text(self, doc):
        from src.engine.doc.models import BlockType

        table = [b for b in doc.pages[0].blocks if b.type == BlockType.TABLE][0]
        texts = [c.get("text", "") for c in table.meta["cells"]]
        assert any(t for t in texts), "At least one cell should have text"

    # ── Page layout ───────────────────────────────────────────

    def test_page_layout_in_metadata(self, doc):
        assert "page_layout" in doc.metadata
        layout = doc.metadata["page_layout"]
        assert "width_mm" in layout
        assert "height_mm" in layout
        # A4 should be approximately 210x297mm
        assert 200 < layout["width_mm"] < 220
        assert 290 < layout["height_mm"] < 305


# ── Ingest integration ─────────────────────────────────────────


@pytest.mark.skipif(not REFERENCE_HWP.exists(), reason="reference HWP not available")
class TestHWPIngest:
    def test_ingest_hwp_file(self):
        from src.engine.doc.ingest import ingest

        doc = ingest(REFERENCE_HWP)
        assert len(doc.pages) == 1
        assert doc.metadata["format"] == "hwp"
        assert doc.metadata["source"] == str(REFERENCE_HWP)

    def test_detect_hwp_format(self):
        from src.engine.doc.ingest import detect_format

        assert detect_format(REFERENCE_HWP) == "hwp"

    def test_hwp_in_registry(self):
        from src.engine.doc.ingest import PARSER_REGISTRY

        assert "hwp" in PARSER_REGISTRY
