"""Tests for Markdown parser and Parser protocol.

Verifies:
- MarkdownParser conforms to Parser protocol
- Each block type is correctly parsed from standard markdown
- Edge cases (empty input, mixed content, nested structures)
"""
from __future__ import annotations

import pytest

# ── Parser protocol conformance ─────────────────────────────────


class TestParserProtocol:
    def test_markdown_parser_has_parse_method(self):
        from src.engine.doc.parsers.markdown import MarkdownParser

        parser = MarkdownParser()
        assert callable(getattr(parser, "parse", None))

    def test_parse_returns_universal_doc(self):
        from src.engine.doc.models import UniversalDoc
        from src.engine.doc.parsers.markdown import MarkdownParser

        doc = MarkdownParser().parse("# Hello")
        assert isinstance(doc, UniversalDoc)

    def test_markdown_parser_satisfies_protocol(self):
        from src.engine.doc.parsers.base import Parser
        from src.engine.doc.parsers.markdown import MarkdownParser

        parser = MarkdownParser()
        assert isinstance(parser, Parser)


# ── Heading parsing ─────────────────────────────────────────────


class TestHeadingParsing:
    @pytest.mark.parametrize("level", [1, 2, 3, 4, 5, 6])
    def test_heading_levels(self, level):
        from src.engine.doc.models import BlockType
        from src.engine.doc.parsers.markdown import MarkdownParser

        md = "#" * level + " Heading\n"
        doc = MarkdownParser().parse(md)
        blocks = doc.pages[0].blocks
        assert len(blocks) == 1
        assert blocks[0].type == BlockType.HEADING
        assert blocks[0].content == "Heading"
        assert blocks[0].meta["level"] == level

    def test_multiple_headings(self):
        from src.engine.doc.models import BlockType
        from src.engine.doc.parsers.markdown import MarkdownParser

        md = "# First\n\n## Second\n"
        doc = MarkdownParser().parse(md)
        blocks = doc.pages[0].blocks
        heading_blocks = [b for b in blocks if b.type == BlockType.HEADING]
        assert len(heading_blocks) == 2
        assert heading_blocks[0].meta["level"] == 1
        assert heading_blocks[1].meta["level"] == 2


# ── Paragraph parsing ───────────────────────────────────────────


class TestParagraphParsing:
    def test_single_paragraph(self):
        from src.engine.doc.models import BlockType
        from src.engine.doc.parsers.markdown import MarkdownParser

        doc = MarkdownParser().parse("Hello world\n")
        blocks = doc.pages[0].blocks
        assert len(blocks) == 1
        assert blocks[0].type == BlockType.PARAGRAPH
        assert "Hello world" in blocks[0].content

    def test_paragraph_preserves_inline_formatting(self):
        from src.engine.doc.models import BlockType
        from src.engine.doc.parsers.markdown import MarkdownParser

        doc = MarkdownParser().parse("Text with **bold** and *italic*\n")
        blocks = doc.pages[0].blocks
        para = blocks[0]
        assert para.type == BlockType.PARAGRAPH
        assert "**bold**" in para.content or "bold" in para.content

    def test_multiple_paragraphs_separated_by_blank_line(self):
        from src.engine.doc.models import BlockType
        from src.engine.doc.parsers.markdown import MarkdownParser

        md = "First paragraph.\n\nSecond paragraph.\n"
        doc = MarkdownParser().parse(md)
        blocks = doc.pages[0].blocks
        paragraphs = [b for b in blocks if b.type == BlockType.PARAGRAPH]
        assert len(paragraphs) == 2


# ── Code block parsing ──────────────────────────────────────────


class TestCodeBlockParsing:
    def test_fenced_code_block(self):
        from src.engine.doc.models import BlockType
        from src.engine.doc.parsers.markdown import MarkdownParser

        md = "```\nprint('hello')\n```\n"
        doc = MarkdownParser().parse(md)
        blocks = doc.pages[0].blocks
        code_blocks = [b for b in blocks if b.type == BlockType.CODE]
        assert len(code_blocks) == 1
        assert "print('hello')" in code_blocks[0].content

    def test_fenced_code_block_with_language(self):
        from src.engine.doc.models import BlockType
        from src.engine.doc.parsers.markdown import MarkdownParser

        md = "```python\ndef foo():\n    pass\n```\n"
        doc = MarkdownParser().parse(md)
        blocks = doc.pages[0].blocks
        code_blocks = [b for b in blocks if b.type == BlockType.CODE]
        assert len(code_blocks) == 1
        assert code_blocks[0].meta["language"] == "python"

    def test_code_block_without_language_has_empty_language(self):
        from src.engine.doc.models import BlockType
        from src.engine.doc.parsers.markdown import MarkdownParser

        md = "```\ncode here\n```\n"
        doc = MarkdownParser().parse(md)
        code_blocks = [b for b in doc.pages[0].blocks if b.type == BlockType.CODE]
        assert code_blocks[0].meta.get("language", "") == ""


# ── Blockquote parsing ──────────────────────────────────────────


class TestQuoteParsing:
    def test_single_line_quote(self):
        from src.engine.doc.models import BlockType
        from src.engine.doc.parsers.markdown import MarkdownParser

        md = "> This is a quote\n"
        doc = MarkdownParser().parse(md)
        blocks = doc.pages[0].blocks
        quotes = [b for b in blocks if b.type == BlockType.QUOTE]
        assert len(quotes) == 1
        assert "This is a quote" in quotes[0].content

    def test_multiline_quote(self):
        from src.engine.doc.models import BlockType
        from src.engine.doc.parsers.markdown import MarkdownParser

        md = "> Line one\n> Line two\n"
        doc = MarkdownParser().parse(md)
        quotes = [b for b in doc.pages[0].blocks if b.type == BlockType.QUOTE]
        assert len(quotes) == 1
        assert "Line one" in quotes[0].content
        assert "Line two" in quotes[0].content


# ── List parsing ────────────────────────────────────────────────


class TestListParsing:
    def test_unordered_list(self):
        from src.engine.doc.models import BlockType
        from src.engine.doc.parsers.markdown import MarkdownParser

        md = "- apple\n- banana\n- cherry\n"
        doc = MarkdownParser().parse(md)
        lists = [b for b in doc.pages[0].blocks if b.type == BlockType.LIST]
        assert len(lists) == 1
        assert lists[0].meta["ordered"] is False
        assert "apple" in lists[0].content

    def test_ordered_list(self):
        from src.engine.doc.models import BlockType
        from src.engine.doc.parsers.markdown import MarkdownParser

        md = "1. first\n2. second\n3. third\n"
        doc = MarkdownParser().parse(md)
        lists = [b for b in doc.pages[0].blocks if b.type == BlockType.LIST]
        assert len(lists) == 1
        assert lists[0].meta["ordered"] is True
        assert "first" in lists[0].content

    def test_list_items_in_content(self):
        from src.engine.doc.models import BlockType
        from src.engine.doc.parsers.markdown import MarkdownParser

        md = "- one\n- two\n"
        doc = MarkdownParser().parse(md)
        lists = [b for b in doc.pages[0].blocks if b.type == BlockType.LIST]
        # items should be extractable from content
        items = lists[0].content.split("\n")
        assert len([i for i in items if i.strip()]) == 2


# ── Table parsing ───────────────────────────────────────────────


class TestTableParsing:
    def test_simple_table(self):
        from src.engine.doc.models import BlockType
        from src.engine.doc.parsers.markdown import MarkdownParser

        md = "| Name | Age |\n|------|-----|\n| Alice | 30 |\n| Bob | 25 |\n"
        doc = MarkdownParser().parse(md)
        tables = [b for b in doc.pages[0].blocks if b.type == BlockType.TABLE]
        assert len(tables) == 1
        assert tables[0].meta["headers"] == ["Name", "Age"]
        assert len(tables[0].meta["rows"]) == 2

    def test_table_row_values(self):
        from src.engine.doc.models import BlockType
        from src.engine.doc.parsers.markdown import MarkdownParser

        md = "| X | Y |\n|---|---|\n| 1 | 2 |\n"
        doc = MarkdownParser().parse(md)
        tables = [b for b in doc.pages[0].blocks if b.type == BlockType.TABLE]
        assert tables[0].meta["rows"][0] == ["1", "2"]


# ── Image parsing ───────────────────────────────────────────────


class TestImageParsing:
    def test_inline_image(self):
        from src.engine.doc.models import BlockType
        from src.engine.doc.parsers.markdown import MarkdownParser

        md = "![alt text](image.png)\n"
        doc = MarkdownParser().parse(md)
        images = [b for b in doc.pages[0].blocks if b.type == BlockType.IMAGE]
        assert len(images) == 1
        assert images[0].meta["src"] == "image.png"
        assert images[0].meta["alt"] == "alt text"

    def test_image_with_empty_alt(self):
        from src.engine.doc.models import BlockType
        from src.engine.doc.parsers.markdown import MarkdownParser

        md = "![](photo.jpg)\n"
        doc = MarkdownParser().parse(md)
        images = [b for b in doc.pages[0].blocks if b.type == BlockType.IMAGE]
        assert images[0].meta["src"] == "photo.jpg"
        assert images[0].meta["alt"] == ""


# ── Mixed / integration ────────────────────────────────────────


class TestMixedContent:
    def test_full_document_all_block_types(self, sample_markdown):
        from src.engine.doc.models import BlockType
        from src.engine.doc.parsers.markdown import MarkdownParser

        doc = MarkdownParser().parse(sample_markdown)
        assert len(doc.pages) >= 1

        blocks = doc.pages[0].blocks
        types_found = {b.type for b in blocks}

        assert BlockType.HEADING in types_found
        assert BlockType.PARAGRAPH in types_found
        assert BlockType.CODE in types_found
        assert BlockType.QUOTE in types_found
        assert BlockType.LIST in types_found
        assert BlockType.TABLE in types_found
        assert BlockType.IMAGE in types_found

    def test_block_order_matches_source(self, sample_markdown):
        from src.engine.doc.models import BlockType
        from src.engine.doc.parsers.markdown import MarkdownParser

        doc = MarkdownParser().parse(sample_markdown)
        blocks = doc.pages[0].blocks

        # First block should be the h1 heading
        assert blocks[0].type == BlockType.HEADING
        assert blocks[0].meta["level"] == 1

    def test_document_has_single_page(self, sample_markdown):
        from src.engine.doc.parsers.markdown import MarkdownParser

        doc = MarkdownParser().parse(sample_markdown)
        assert len(doc.pages) == 1


# ── Edge cases ──────────────────────────────────────────────────


class TestEdgeCases:
    def test_empty_input_returns_empty_doc(self, empty_markdown):
        from src.engine.doc.parsers.markdown import MarkdownParser

        doc = MarkdownParser().parse(empty_markdown)
        assert len(doc.pages) == 0 or len(doc.pages[0].blocks) == 0

    def test_whitespace_only_input(self):
        from src.engine.doc.parsers.markdown import MarkdownParser

        doc = MarkdownParser().parse("   \n\n  \n")
        assert len(doc.pages) == 0 or len(doc.pages[0].blocks) == 0

    def test_heading_only(self, heading_only_markdown):
        from src.engine.doc.models import BlockType
        from src.engine.doc.parsers.markdown import MarkdownParser

        doc = MarkdownParser().parse(heading_only_markdown)
        blocks = doc.pages[0].blocks
        assert len(blocks) == 1
        assert blocks[0].type == BlockType.HEADING

    def test_consecutive_code_blocks(self):
        from src.engine.doc.models import BlockType
        from src.engine.doc.parsers.markdown import MarkdownParser

        md = "```\nblock1\n```\n\n```\nblock2\n```\n"
        doc = MarkdownParser().parse(md)
        code_blocks = [b for b in doc.pages[0].blocks if b.type == BlockType.CODE]
        assert len(code_blocks) == 2
