"""Tests for PDF parser (pdfminer.six backend)."""
from __future__ import annotations

from pathlib import Path

import pytest

REFERENCE_PDF = Path(__file__).resolve().parent / "reference_data" / "pdf" / "포테이토크래프트_사업자.pdf"


# ── Protocol conformance ──────────────────────────────────────


class TestPDFProtocol:
    def test_implements_binary_parser(self):
        from src.engine.doc.parsers.base import BinaryParser
        from src.engine.doc.parsers.pdf import PDFParser

        assert isinstance(PDFParser(), BinaryParser)

    def test_has_parse_bytes_method(self):
        from src.engine.doc.parsers.pdf import PDFParser

        parser = PDFParser()
        assert callable(getattr(parser, "parse_bytes", None))


# ── Edge cases ─────────────────────────────────────────────────


class TestPDFEdgeCases:
    def test_empty_bytes_raises(self):
        from src.engine.doc.parsers.pdf import PDFParser

        with pytest.raises(ValueError):
            PDFParser().parse_bytes(b"")

    def test_garbage_bytes_raises(self):
        from src.engine.doc.parsers.pdf import PDFParser

        with pytest.raises(ValueError):
            PDFParser().parse_bytes(b"\x00" * 512)

    def test_corrupt_content_stream_maps_to_value_error(self):
        # Structurally valid enough to pass the encryption guard and build a
        # PDFDocument, but the page content stream holds a malformed dict that
        # pdfminer only chokes on during layout analysis (PSSyntaxError). The
        # extract_pages guard must map that pdfminer exception to ValueError.
        from src.engine.doc.parsers.pdf import PDFParser

        corrupt = (
            b"%PDF-1.4\n"
            b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
            b"/Contents 4 0 R>>endobj\n"
            b"4 0 obj<</Length 8>>stream\n<< /A >>\nendstream endobj\n"
            b"trailer<</Root 1 0 R>>\n%%EOF"
        )
        with pytest.raises(ValueError):
            PDFParser().parse_bytes(corrupt)


# ── Heading heuristic (synthetic, pure function) ───────────────


class TestHeadingHeuristic:
    def test_no_headings_when_uniform(self):
        from src.engine.doc.parsers.pdf import infer_heading_levels

        sizes = [10.0, 10.0, 10.0, 10.0]
        lines = [1, 2, 1, 3]
        assert infer_heading_levels(sizes, lines) == [None, None, None, None]

    def test_single_large_line_is_level_one(self):
        from src.engine.doc.parsers.pdf import infer_heading_levels

        # body median 10 -> threshold 13.0; 20 >= 13 and single line
        sizes = [20.0, 10.0, 10.0, 10.0]
        lines = [1, 1, 1, 1]
        assert infer_heading_levels(sizes, lines) == [1, None, None, None]

    def test_multiple_sizes_ranked_one_to_three(self):
        from src.engine.doc.parsers.pdf import infer_heading_levels

        # body-dominated median 10 -> threshold 13.0
        # qualifying single-line sizes: 24->1, 20->2, 17->3
        sizes = [24.0, 20.0, 17.0, 10.0, 10.0, 10.0, 10.0, 10.0]
        lines = [1, 1, 1, 1, 1, 1, 1, 1]
        assert infer_heading_levels(sizes, lines) == [
            1, 2, 3, None, None, None, None, None,
        ]

    def test_level_capped_at_three(self):
        from src.engine.doc.parsers.pdf import infer_heading_levels

        # four distinct large single-line sizes (median stays 10) -> 4th capped at 3
        sizes = [40.0, 30.0, 20.0, 16.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0]
        lines = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
        levels = infer_heading_levels(sizes, lines)
        assert levels[:4] == [1, 2, 3, 3]

    def test_multiline_large_block_not_heading(self):
        from src.engine.doc.parsers.pdf import infer_heading_levels

        # 20pt but two lines -> not a heading (single-line requirement)
        sizes = [20.0, 10.0, 10.0]
        lines = [2, 1, 1]
        assert infer_heading_levels(sizes, lines) == [None, None, None]

    def test_empty_input(self):
        from src.engine.doc.parsers.pdf import infer_heading_levels

        assert infer_heading_levels([], []) == []


# ── Reference file parsing ─────────────────────────────────────


@pytest.mark.skipif(not REFERENCE_PDF.exists(), reason="reference PDF not available")
class TestPDFReferenceFile:
    @pytest.fixture(scope="class")
    def doc(self):
        from src.engine.doc.parsers.pdf import PDFParser

        return PDFParser().parse_bytes(REFERENCE_PDF.read_bytes())

    def test_returns_universal_doc(self, doc):
        from src.engine.doc.models import UniversalDoc

        assert isinstance(doc, UniversalDoc)

    def test_has_pages(self, doc):
        assert len(doc.pages) > 0

    def test_has_paragraph_blocks(self, doc):
        from src.engine.doc.models import BlockType

        types = {b.type for b in doc.pages[0].blocks}
        assert BlockType.PARAGRAPH in types

    # ── Text extraction (real content from the reference file) ──

    def test_contains_business_name(self, doc):
        all_text = " ".join(b.content for b in doc.pages[0].blocks)
        assert "포테이토크래프트" in all_text

    def test_contains_representative_name(self, doc):
        all_text = " ".join(b.content for b in doc.pages[0].blocks)
        assert "박연미" in all_text

    def test_contains_registration_number(self, doc):
        all_text = " ".join(b.content for b in doc.pages[0].blocks)
        assert "370-08-03144" in all_text

    # ── Heading inference on the reference ─────────────────────

    def test_has_heading_with_level(self, doc):
        from src.engine.doc.models import BlockType

        headings = [b for b in doc.pages[0].blocks if b.type == BlockType.HEADING]
        assert len(headings) >= 1
        for h in headings:
            assert h.meta["level"] in (1, 2, 3)

    # ── Image detection ────────────────────────────────────────

    def test_images_in_metadata(self, doc):
        assert "images" in doc.metadata
        assert isinstance(doc.metadata["images"], list)
        assert len(doc.metadata["images"]) > 0

    # ── Page layout ───────────────────────────────────────────

    def test_page_layout_in_metadata(self, doc):
        assert "page_layout" in doc.metadata
        layout = doc.metadata["page_layout"]
        assert "width_pt" in layout
        assert "height_pt" in layout
        # A4 in points is approx 595 x 842
        assert 580 < layout["width_pt"] < 610
        assert 820 < layout["height_pt"] < 860


# ── Ingest integration ─────────────────────────────────────────


@pytest.mark.skipif(not REFERENCE_PDF.exists(), reason="reference PDF not available")
class TestPDFIngest:
    def test_ingest_pdf_file(self):
        from src.engine.doc.ingest import ingest

        doc = ingest(REFERENCE_PDF)
        assert len(doc.pages) > 0
        assert doc.metadata["format"] == "pdf"
        assert doc.metadata["source"] == str(REFERENCE_PDF)

    def test_detect_pdf_format(self):
        from src.engine.doc.ingest import detect_format

        assert detect_format(REFERENCE_PDF) == "pdf"

    def test_pdf_in_registry(self):
        from src.engine.doc.ingest import PARSER_REGISTRY

        assert "pdf" in PARSER_REGISTRY
