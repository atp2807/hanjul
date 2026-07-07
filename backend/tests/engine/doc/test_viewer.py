"""Tests for viewer.py — UniversalDoc → HTML rendering.

Verifies:
- Each BlockType renders to the correct HTML element
- Block.meta contracts are respected (level, language, ordered, headers/rows, src/alt)
- HTML escaping prevents XSS
- Full document rendering (multi-page, multi-block)
- Edge cases (empty doc, empty page, empty content)
"""
from __future__ import annotations

from src.engine.doc.models import Block, BlockType, Page, UniversalDoc

# ── render_block: HEADING ─────────────────────────────────────


class TestRenderHeading:
    def test_heading_level_1(self):
        from src.engine.doc.viewer import render_block

        block = Block(type=BlockType.HEADING, content="Title", meta={"level": 1})
        html = render_block(block)
        assert html == "<h1>Title</h1>"

    def test_heading_level_2(self):
        from src.engine.doc.viewer import render_block

        block = Block(type=BlockType.HEADING, content="Subtitle", meta={"level": 2})
        html = render_block(block)
        assert html == "<h2>Subtitle</h2>"

    def test_heading_level_6(self):
        from src.engine.doc.viewer import render_block

        block = Block(type=BlockType.HEADING, content="Deep", meta={"level": 6})
        html = render_block(block)
        assert html == "<h6>Deep</h6>"

    def test_heading_defaults_to_h1_when_no_level(self):
        from src.engine.doc.viewer import render_block

        block = Block(type=BlockType.HEADING, content="No level", meta={})
        html = render_block(block)
        assert html == "<h1>No level</h1>"

    def test_heading_escapes_html(self):
        from src.engine.doc.viewer import render_block

        block = Block(
            type=BlockType.HEADING,
            content="<script>alert(1)</script>",
            meta={"level": 1},
        )
        html = render_block(block)
        assert "<script>" not in html
        assert "&lt;script&gt;" in html


# ── render_block: PARAGRAPH ───────────────────────────────────


class TestRenderParagraph:
    def test_simple_paragraph(self):
        from src.engine.doc.viewer import render_block

        block = Block(type=BlockType.PARAGRAPH, content="Hello world")
        html = render_block(block)
        assert html == "<p>Hello world</p>"

    def test_paragraph_escapes_html(self):
        from src.engine.doc.viewer import render_block

        block = Block(type=BlockType.PARAGRAPH, content='<img src=x onerror="alert(1)">')
        html = render_block(block)
        assert "<img" not in html
        assert "&lt;img" in html

    def test_multiline_paragraph(self):
        from src.engine.doc.viewer import render_block

        block = Block(type=BlockType.PARAGRAPH, content="Line 1\nLine 2")
        html = render_block(block)
        assert "<p>" in html
        assert "Line 1" in html
        assert "Line 2" in html


# ── render_block: CODE ────────────────────────────────────────


class TestRenderCode:
    def test_code_block_basic(self):
        from src.engine.doc.viewer import render_block

        block = Block(type=BlockType.CODE, content="x = 1", meta={"language": "python"})
        html = render_block(block)
        assert "<pre>" in html
        assert "<code" in html
        assert "x = 1" in html

    def test_code_block_has_language_class(self):
        from src.engine.doc.viewer import render_block

        block = Block(type=BlockType.CODE, content="let x = 1;", meta={"language": "javascript"})
        html = render_block(block)
        assert 'class="language-javascript"' in html

    def test_code_block_no_language(self):
        from src.engine.doc.viewer import render_block

        block = Block(type=BlockType.CODE, content="plain code", meta={})
        html = render_block(block)
        assert "<pre>" in html
        assert "<code>" in html

    def test_code_block_empty_language(self):
        from src.engine.doc.viewer import render_block

        block = Block(type=BlockType.CODE, content="code", meta={"language": ""})
        html = render_block(block)
        assert "<code>" in html
        assert "language-" not in html

    def test_code_block_escapes_html(self):
        from src.engine.doc.viewer import render_block

        block = Block(type=BlockType.CODE, content="<div>injected</div>", meta={"language": "html"})
        html = render_block(block)
        assert "<div>injected</div>" not in html
        assert "&lt;div&gt;" in html


# ── render_block: IMAGE ───────────────────────────────────────


class TestRenderImage:
    def test_image_renders_img_tag(self):
        from src.engine.doc.viewer import render_block

        block = Block(type=BlockType.IMAGE, content="", meta={"src": "photo.png", "alt": "A photo"})
        html = render_block(block)
        assert "<img" in html
        assert 'src="photo.png"' in html
        assert 'alt="A photo"' in html

    def test_image_escapes_src(self):
        from src.engine.doc.viewer import render_block

        block = Block(
            type=BlockType.IMAGE,
            content="",
            meta={"src": '" onerror="alert(1)', "alt": "x"},
        )
        html = render_block(block)
        assert 'onerror=' not in html

    def test_image_escapes_alt(self):
        from src.engine.doc.viewer import render_block

        block = Block(
            type=BlockType.IMAGE,
            content="",
            meta={"src": "img.png", "alt": '<script>"</script>'},
        )
        html = render_block(block)
        assert "<script>" not in html


# ── render_block: QUOTE ───────────────────────────────────────


class TestRenderQuote:
    def test_blockquote(self):
        from src.engine.doc.viewer import render_block

        block = Block(type=BlockType.QUOTE, content="Wise words")
        html = render_block(block)
        assert "<blockquote>" in html
        assert "Wise words" in html
        assert "</blockquote>" in html

    def test_blockquote_escapes_html(self):
        from src.engine.doc.viewer import render_block

        block = Block(type=BlockType.QUOTE, content="<b>bold</b>")
        html = render_block(block)
        assert "<b>" not in html
        assert "&lt;b&gt;" in html


# ── render_block: LIST ────────────────────────────────────────


class TestRenderList:
    def test_unordered_list(self):
        from src.engine.doc.viewer import render_block

        block = Block(type=BlockType.LIST, content="apple\nbanana\ncherry", meta={"ordered": False})
        html = render_block(block)
        assert "<ul>" in html
        assert "</ul>" in html
        assert html.count("<li>") == 3
        assert "apple" in html
        assert "banana" in html
        assert "cherry" in html

    def test_ordered_list(self):
        from src.engine.doc.viewer import render_block

        block = Block(type=BlockType.LIST, content="first\nsecond\nthird", meta={"ordered": True})
        html = render_block(block)
        assert "<ol>" in html
        assert "</ol>" in html
        assert html.count("<li>") == 3

    def test_list_defaults_to_unordered(self):
        from src.engine.doc.viewer import render_block

        block = Block(type=BlockType.LIST, content="item", meta={})
        html = render_block(block)
        assert "<ul>" in html

    def test_list_escapes_items(self):
        from src.engine.doc.viewer import render_block

        block = Block(type=BlockType.LIST, content="<em>bold</em>\nnormal", meta={"ordered": False})
        html = render_block(block)
        assert "<em>" not in html
        assert "&lt;em&gt;" in html


# ── render_block: TABLE ───────────────────────────────────────


class TestRenderTable:
    def test_table_structure(self):
        from src.engine.doc.viewer import render_block

        block = Block(
            type=BlockType.TABLE,
            content="",
            meta={
                "headers": ["Name", "Age"],
                "rows": [["Alice", "30"], ["Bob", "25"]],
            },
        )
        html = render_block(block)
        assert "<table>" in html
        assert "</table>" in html
        assert "<thead>" in html
        assert "<tbody>" in html
        assert "<th>" in html
        assert html.count("<th>") == 2
        assert html.count("<tr>") == 3  # 1 header row + 2 data rows

    def test_table_header_content(self):
        from src.engine.doc.viewer import render_block

        block = Block(
            type=BlockType.TABLE,
            content="",
            meta={"headers": ["Col1", "Col2"], "rows": []},
        )
        html = render_block(block)
        assert "Col1" in html
        assert "Col2" in html

    def test_table_row_content(self):
        from src.engine.doc.viewer import render_block

        block = Block(
            type=BlockType.TABLE,
            content="",
            meta={"headers": ["X"], "rows": [["val1"], ["val2"]]},
        )
        html = render_block(block)
        assert "val1" in html
        assert "val2" in html

    def test_table_escapes_cells(self):
        from src.engine.doc.viewer import render_block

        block = Block(
            type=BlockType.TABLE,
            content="",
            meta={"headers": ["<b>H</b>"], "rows": [["<script>x</script>"]]},
        )
        html = render_block(block)
        assert "<b>" not in html
        assert "<script>" not in html
        assert "&lt;b&gt;" in html


# ── render_doc ────────────────────────────────────────────────


class TestRenderDoc:
    def test_empty_doc(self):
        from src.engine.doc.viewer import render_doc

        doc = UniversalDoc()
        html = render_doc(doc)
        assert isinstance(html, str)

    def test_single_page_single_block(self):
        from src.engine.doc.viewer import render_doc

        doc = UniversalDoc(pages=[
            Page(blocks=[Block(type=BlockType.PARAGRAPH, content="Hello")])
        ])
        html = render_doc(doc)
        assert "<p>Hello</p>" in html

    def test_multiple_blocks_rendered_in_order(self):
        from src.engine.doc.viewer import render_doc

        doc = UniversalDoc(pages=[
            Page(blocks=[
                Block(type=BlockType.HEADING, content="Title", meta={"level": 1}),
                Block(type=BlockType.PARAGRAPH, content="Body text"),
            ])
        ])
        html = render_doc(doc)
        title_pos = html.index("<h1>Title</h1>")
        body_pos = html.index("<p>Body text</p>")
        assert title_pos < body_pos

    def test_multiple_pages(self):
        from src.engine.doc.viewer import render_doc

        doc = UniversalDoc(pages=[
            Page(blocks=[Block(type=BlockType.PARAGRAPH, content="Page 1")]),
            Page(blocks=[Block(type=BlockType.PARAGRAPH, content="Page 2")]),
        ])
        html = render_doc(doc)
        assert "Page 1" in html
        assert "Page 2" in html

    def test_empty_page_no_error(self):
        from src.engine.doc.viewer import render_doc

        doc = UniversalDoc(pages=[Page()])
        html = render_doc(doc)
        assert isinstance(html, str)

    def test_all_block_types_together(self):
        from src.engine.doc.viewer import render_doc

        doc = UniversalDoc(pages=[Page(blocks=[
            Block(type=BlockType.HEADING, content="H", meta={"level": 1}),
            Block(type=BlockType.PARAGRAPH, content="P"),
            Block(type=BlockType.CODE, content="C", meta={"language": "py"}),
            Block(type=BlockType.IMAGE, content="", meta={"src": "i.png", "alt": "I"}),
            Block(type=BlockType.QUOTE, content="Q"),
            Block(type=BlockType.LIST, content="L1\nL2", meta={"ordered": False}),
            Block(type=BlockType.TABLE, content="", meta={"headers": ["T"], "rows": [["R"]]}),
        ])])
        html = render_doc(doc)
        assert "<h1>" in html
        assert "<p>" in html
        assert "<pre>" in html
        assert "<img" in html
        assert "<blockquote>" in html
        assert "<ul>" in html
        assert "<table>" in html
