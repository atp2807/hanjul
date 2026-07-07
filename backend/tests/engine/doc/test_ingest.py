"""Tests for Ingest orchestrator.

Verifies:
- Format detection by file extension
- Parser registry maps extensions to correct parsers
- ingest() reads file and returns UniversalDoc via correct parser
- Unsupported format raises ValueError
- Edge cases (case-insensitive extension, missing file)
"""
from __future__ import annotations

from pathlib import Path

import pytest

# ── Format detection ────────────────────────────────────────────


class TestFormatDetection:
    def test_detect_markdown_md(self):
        from src.engine.doc.ingest import detect_format

        assert detect_format(Path("readme.md")) == "md"

    def test_detect_text_txt(self):
        from src.engine.doc.ingest import detect_format

        assert detect_format(Path("notes.txt")) == "txt"

    def test_detect_uppercase_extension(self):
        from src.engine.doc.ingest import detect_format

        assert detect_format(Path("README.MD")) == "md"

    def test_detect_mixed_case_extension(self):
        from src.engine.doc.ingest import detect_format

        assert detect_format(Path("file.Txt")) == "txt"

    def test_unsupported_format_raises(self):
        from src.engine.doc.ingest import detect_format

        with pytest.raises(ValueError, match="xyz"):
            detect_format(Path("document.xyz"))

    def test_no_extension_raises(self):
        from src.engine.doc.ingest import detect_format

        with pytest.raises(ValueError):
            detect_format(Path("Makefile"))


# ── Parser registry ─────────────────────────────────────────────


class TestParserRegistry:
    def test_registry_contains_md(self):
        from src.engine.doc.ingest import PARSER_REGISTRY

        assert "md" in PARSER_REGISTRY

    def test_registry_contains_txt(self):
        from src.engine.doc.ingest import PARSER_REGISTRY

        assert "txt" in PARSER_REGISTRY

    def test_md_registry_entry_is_markdown_parser(self):
        from src.engine.doc.ingest import PARSER_REGISTRY
        from src.engine.doc.parsers.base import Parser

        parser = PARSER_REGISTRY["md"]
        assert isinstance(parser, Parser)

    def test_txt_registry_entry_is_text_parser(self):
        from src.engine.doc.ingest import PARSER_REGISTRY
        from src.engine.doc.parsers.base import Parser

        parser = PARSER_REGISTRY["txt"]
        assert isinstance(parser, Parser)

    def test_get_parser_returns_correct_parser_for_md(self):
        from src.engine.doc.ingest import get_parser
        from src.engine.doc.parsers.markdown import MarkdownParser

        parser = get_parser("md")
        assert isinstance(parser, MarkdownParser)

    def test_get_parser_returns_correct_parser_for_txt(self):
        from src.engine.doc.ingest import get_parser
        from src.engine.doc.parsers.text import TextParser

        parser = get_parser("txt")
        assert isinstance(parser, TextParser)

    def test_get_parser_unsupported_raises(self):
        from src.engine.doc.ingest import get_parser

        with pytest.raises(ValueError, match="xyz"):
            get_parser("xyz")

    def test_binary_formats_registered(self):
        from src.engine.doc.ingest import BINARY_FORMATS, PARSER_REGISTRY
        from src.engine.doc.parsers.base import BinaryParser

        assert {
            "hwp", "hwpx", "docx", "pdf", "html", "htm", "csv", "pptx", "xlsx",
        } == BINARY_FORMATS
        for fmt in BINARY_FORMATS:
            assert isinstance(PARSER_REGISTRY[fmt], BinaryParser)


# ── Ingest orchestrator ─────────────────────────────────────────


class TestIngest:
    def test_ingest_markdown_file(self, tmp_path):
        from src.engine.doc.ingest import ingest
        from src.engine.doc.models import BlockType, UniversalDoc

        md_file = tmp_path / "test.md"
        md_file.write_text("# Hello\n\nWorld\n")

        doc = ingest(md_file)
        assert isinstance(doc, UniversalDoc)
        assert len(doc.pages) >= 1
        assert doc.pages[0].blocks[0].type == BlockType.HEADING

    def test_ingest_text_file(self, tmp_path):
        from src.engine.doc.ingest import ingest
        from src.engine.doc.models import BlockType, UniversalDoc

        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Hello world\n\nSecond paragraph")

        doc = ingest(txt_file)
        assert isinstance(doc, UniversalDoc)
        assert len(doc.pages) >= 1
        assert doc.pages[0].blocks[0].type == BlockType.PARAGRAPH

    def test_ingest_unsupported_format_raises(self, tmp_path):
        from src.engine.doc.ingest import ingest

        pdf_file = tmp_path / "doc.pdf"
        pdf_file.write_bytes(b"%PDF-1.4")

        with pytest.raises(ValueError):
            ingest(pdf_file)

    def test_ingest_nonexistent_file_raises(self):
        from src.engine.doc.ingest import ingest

        with pytest.raises(FileNotFoundError):
            ingest(Path("/nonexistent/file.md"))

    def test_ingest_preserves_content(self, tmp_path):
        from src.engine.doc.ingest import ingest

        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Exact content here")

        doc = ingest(txt_file)
        assert doc.pages[0].blocks[0].content == "Exact content here"

    def test_ingest_empty_file(self, tmp_path):
        from src.engine.doc.ingest import ingest

        txt_file = tmp_path / "empty.txt"
        txt_file.write_text("")

        doc = ingest(txt_file)
        assert len(doc.pages) == 0 or len(doc.pages[0].blocks) == 0

    def test_ingest_returns_metadata_with_source(self, tmp_path):
        from src.engine.doc.ingest import ingest

        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Hello")

        doc = ingest(txt_file)
        assert "source" in doc.metadata
        assert doc.metadata["source"] == str(txt_file)

    def test_ingest_returns_metadata_with_format(self, tmp_path):
        from src.engine.doc.ingest import ingest

        md_file = tmp_path / "test.md"
        md_file.write_text("# Title")

        doc = ingest(md_file)
        assert "format" in doc.metadata
        assert doc.metadata["format"] == "md"
