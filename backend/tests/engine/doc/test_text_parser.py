"""Tests for plain-text parser.

Verifies:
- TextParser conforms to Parser protocol
- Plain text is split into PARAGRAPH blocks by blank lines
- Edge cases (empty input, whitespace-only, single line)
"""
from __future__ import annotations

# ── Parser protocol conformance ─────────────────────────────────


class TestParserProtocol:
    def test_text_parser_has_parse_method(self):
        from src.engine.doc.parsers.text import TextParser

        parser = TextParser()
        assert callable(getattr(parser, "parse", None))

    def test_parse_returns_universal_doc(self):
        from src.engine.doc.models import UniversalDoc
        from src.engine.doc.parsers.text import TextParser

        doc = TextParser().parse("Hello world")
        assert isinstance(doc, UniversalDoc)

    def test_text_parser_satisfies_protocol(self):
        from src.engine.doc.parsers.base import Parser
        from src.engine.doc.parsers.text import TextParser

        parser = TextParser()
        assert isinstance(parser, Parser)


# ── Paragraph splitting ─────────────────────────────────────────


class TestParagraphParsing:
    def test_single_paragraph(self):
        from src.engine.doc.models import BlockType
        from src.engine.doc.parsers.text import TextParser

        doc = TextParser().parse("Hello world")
        blocks = doc.pages[0].blocks
        assert len(blocks) == 1
        assert blocks[0].type == BlockType.PARAGRAPH
        assert blocks[0].content == "Hello world"

    def test_multiple_paragraphs_separated_by_blank_line(self):
        from src.engine.doc.models import BlockType
        from src.engine.doc.parsers.text import TextParser

        text = "First paragraph.\n\nSecond paragraph."
        doc = TextParser().parse(text)
        blocks = doc.pages[0].blocks
        paragraphs = [b for b in blocks if b.type == BlockType.PARAGRAPH]
        assert len(paragraphs) == 2
        assert paragraphs[0].content == "First paragraph."
        assert paragraphs[1].content == "Second paragraph."

    def test_multiple_blank_lines_treated_as_single_separator(self):
        from src.engine.doc.models import BlockType
        from src.engine.doc.parsers.text import TextParser

        text = "Para one.\n\n\n\nPara two."
        doc = TextParser().parse(text)
        blocks = doc.pages[0].blocks
        paragraphs = [b for b in blocks if b.type == BlockType.PARAGRAPH]
        assert len(paragraphs) == 2

    def test_multiline_paragraph_preserves_content(self):
        from src.engine.doc.models import BlockType
        from src.engine.doc.parsers.text import TextParser

        text = "Line one\nLine two\nLine three"
        doc = TextParser().parse(text)
        blocks = doc.pages[0].blocks
        assert len(blocks) == 1
        assert blocks[0].type == BlockType.PARAGRAPH
        assert blocks[0].content == "Line one\nLine two\nLine three"

    def test_paragraph_has_no_meta(self):
        from src.engine.doc.parsers.text import TextParser

        doc = TextParser().parse("Simple text")
        block = doc.pages[0].blocks[0]
        assert block.meta == {}


# ── Document structure ──────────────────────────────────────────


class TestDocumentStructure:
    def test_single_page_output(self):
        from src.engine.doc.parsers.text import TextParser

        doc = TextParser().parse("Hello\n\nWorld")
        assert len(doc.pages) == 1

    def test_block_order_matches_source(self):
        from src.engine.doc.parsers.text import TextParser

        text = "First.\n\nSecond.\n\nThird."
        doc = TextParser().parse(text)
        blocks = doc.pages[0].blocks
        assert blocks[0].content == "First."
        assert blocks[1].content == "Second."
        assert blocks[2].content == "Third."

    def test_all_blocks_are_paragraph_type(self):
        from src.engine.doc.models import BlockType
        from src.engine.doc.parsers.text import TextParser

        text = "A\n\nB\n\nC"
        doc = TextParser().parse(text)
        for block in doc.pages[0].blocks:
            assert block.type == BlockType.PARAGRAPH


# ── Edge cases ──────────────────────────────────────────────────


class TestEdgeCases:
    def test_empty_input_returns_empty_doc(self):
        from src.engine.doc.parsers.text import TextParser

        doc = TextParser().parse("")
        assert len(doc.pages) == 0 or len(doc.pages[0].blocks) == 0

    def test_whitespace_only_input(self):
        from src.engine.doc.parsers.text import TextParser

        doc = TextParser().parse("   \n\n  \n")
        assert len(doc.pages) == 0 or len(doc.pages[0].blocks) == 0

    def test_single_line_no_newline(self):
        from src.engine.doc.parsers.text import TextParser

        doc = TextParser().parse("Just one line")
        blocks = doc.pages[0].blocks
        assert len(blocks) == 1
        assert blocks[0].content == "Just one line"

    def test_trailing_newlines_ignored(self):
        from src.engine.doc.parsers.text import TextParser

        doc = TextParser().parse("Hello\n\n\n")
        blocks = doc.pages[0].blocks
        assert len(blocks) == 1
        assert blocks[0].content == "Hello"

    def test_leading_newlines_ignored(self):
        from src.engine.doc.parsers.text import TextParser

        doc = TextParser().parse("\n\n\nHello")
        blocks = doc.pages[0].blocks
        assert len(blocks) == 1
        assert blocks[0].content == "Hello"
