"""Tests for OLE2 compound document reader."""
from __future__ import annotations

from pathlib import Path

import pytest

REFERENCE_HWP = Path(__file__).resolve().parent / "reference_data" / "hwp" / "복무상황신고서_2512_박연미.hwp"


# ── Signature validation ───────────────────────────────────────


class TestOLE2Validation:
    def test_empty_bytes_raises(self):
        from src.engine.doc.parsers._ole2 import read_ole2

        with pytest.raises(ValueError, match="Not a valid OLE2"):
            read_ole2(b"")

    def test_bad_signature_raises(self):
        from src.engine.doc.parsers._ole2 import read_ole2

        with pytest.raises(ValueError, match="Not a valid OLE2"):
            read_ole2(b"\x00" * 512)

    def test_truncated_file_raises(self):
        from src.engine.doc.parsers._ole2 import read_ole2

        with pytest.raises(ValueError, match="Not a valid OLE2"):
            read_ole2(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 100)


# ── Reference file parsing ─────────────────────────────────────


@pytest.mark.skipif(not REFERENCE_HWP.exists(), reason="reference HWP not available")
class TestOLE2ReferenceFile:
    @pytest.fixture(scope="class")
    def ole2_doc(self):
        from src.engine.doc.parsers._ole2 import read_ole2

        return read_ole2(REFERENCE_HWP.read_bytes())

    def test_streams_not_empty(self, ole2_doc):
        assert len(ole2_doc.streams) > 0

    def test_has_file_header(self, ole2_doc):
        assert "FileHeader" in ole2_doc.streams

    def test_has_body_text_section(self, ole2_doc):
        assert "BodyText/Section0" in ole2_doc.streams

    def test_has_doc_info(self, ole2_doc):
        assert "DocInfo" in ole2_doc.streams

    def test_has_prv_text(self, ole2_doc):
        assert "PrvText" in ole2_doc.streams

    def test_has_bin_data(self, ole2_doc):
        assert "BinData/BIN0001.png" in ole2_doc.streams

    def test_file_header_size(self, ole2_doc):
        assert len(ole2_doc.streams["FileHeader"]) == 256

    def test_file_header_signature(self, ole2_doc):
        fh = ole2_doc.streams["FileHeader"]
        assert fh[:17] == b"HWP Document File"

    def test_section0_size_positive(self, ole2_doc):
        assert len(ole2_doc.streams["BodyText/Section0"]) > 0

    def test_stream_count(self, ole2_doc):
        # 10 streams in reference file
        assert len(ole2_doc.streams) == 10
