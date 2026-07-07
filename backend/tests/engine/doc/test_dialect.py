"""Tests for dialect.py — UniversalDoc <-> dialect HTML v1 round-trip.

Verifies:
- (a) serialize snapshots per BlockType
- (b) parse produces the expected Block structure
- (c) round-trip identity: parse(serialize(doc)) structural equality and
      serialize(parse(html)) string equality on canonical input
- (d) sanitize: script removed, javascript: href rejected, unknown tag unwrap,
      style whitelist
- (e) page flattening
"""
from __future__ import annotations

from pathlib import Path

import pytest
from src.engine.doc.dialect import css_to_style, parse_dialect, serialize_doc, style_to_css
from src.engine.doc.models import Block, BlockType, Page, UniversalDoc

REFERENCE_HWP = Path(__file__).resolve().parent / "reference_data" / "hwp" / "복무상황신고서_2512_박연미.hwp"

ARTICLE_OPEN = '<article data-juldoc="1">'
ARTICLE_CLOSE = "</article>"


def _wrap(inner: str) -> str:
    return ARTICLE_OPEN + inner + ARTICLE_CLOSE


def _one(make_doc, make_page, block: Block) -> UniversalDoc:
    return make_doc(pages=[make_page(blocks=[block])])


# ── (a) serialize snapshots ───────────────────────────────────


class TestSerializeSnapshots:
    def test_heading(self, make_doc, make_page, make_block):
        block = make_block(BlockType.HEADING, "Title", meta={"level": 2})
        assert serialize_doc(_one(make_doc, make_page, block)) == _wrap("<h2>Title</h2>")

    def test_heading_level_clamped(self, make_doc, make_page, make_block):
        block = make_block(BlockType.HEADING, "X", meta={"level": 9})
        assert serialize_doc(_one(make_doc, make_page, block)) == _wrap("<h6>X</h6>")

    def test_paragraph_plain(self, make_doc, make_page, make_block):
        block = make_block(BlockType.PARAGRAPH, "Hello world")
        assert serialize_doc(_one(make_doc, make_page, block)) == _wrap("<p>Hello world</p>")

    def test_paragraph_with_inline(self, make_doc, make_page, make_block):
        block = make_block(BlockType.PARAGRAPH, "a <strong>b</strong> c")
        assert serialize_doc(_one(make_doc, make_page, block)) == _wrap(
            "<p>a <strong>b</strong> c</p>"
        )

    def test_paragraph_with_style(self, make_doc, make_page, make_block):
        # meta["style"] is an abstract dict; dialect serializes it to CSS.
        block = make_block(BlockType.PARAGRAPH, "x", meta={"style": {"bold": True}})
        assert serialize_doc(_one(make_doc, make_page, block)) == _wrap(
            '<p style="font-weight:bold">x</p>'
        )

    def test_code_with_language(self, make_doc, make_page, make_block):
        block = make_block(BlockType.CODE, "x = 1", meta={"language": "python"})
        assert serialize_doc(_one(make_doc, make_page, block)) == _wrap(
            '<pre><code class="language-python">x = 1</code></pre>'
        )

    def test_code_escapes_body(self, make_doc, make_page, make_block):
        block = make_block(BlockType.CODE, "<div>", meta={})
        assert serialize_doc(_one(make_doc, make_page, block)) == _wrap(
            "<pre><code>&lt;div&gt;</code></pre>"
        )

    def test_quote(self, make_doc, make_page, make_block):
        block = make_block(BlockType.QUOTE, "Wise words")
        assert serialize_doc(_one(make_doc, make_page, block)) == _wrap(
            "<blockquote>Wise words</blockquote>"
        )

    def test_unordered_list(self, make_doc, make_page, make_block):
        block = make_block(BlockType.LIST, "a\nb", meta={"ordered": False})
        assert serialize_doc(_one(make_doc, make_page, block)) == _wrap(
            "<ul><li>a</li><li>b</li></ul>"
        )

    def test_ordered_list(self, make_doc, make_page, make_block):
        block = make_block(BlockType.LIST, "a\nb", meta={"ordered": True})
        assert serialize_doc(_one(make_doc, make_page, block)) == _wrap(
            "<ol><li>a</li><li>b</li></ol>"
        )

    def test_image(self, make_doc, make_page, make_block):
        block = make_block(BlockType.IMAGE, "", meta={"src": "photo.png", "alt": "A photo"})
        assert serialize_doc(_one(make_doc, make_page, block)) == _wrap(
            '<img src="photo.png" alt="A photo">'
        )

    def test_simple_table(self, make_doc, make_page, make_block):
        block = make_block(
            BlockType.TABLE, "", meta={"headers": ["Name", "Age"], "rows": [["Alice", "30"]]}
        )
        assert serialize_doc(_one(make_doc, make_page, block)) == _wrap(
            "<table><thead><tr><th>Name</th><th>Age</th></tr></thead>"
            "<tbody><tr><td>Alice</td><td>30</td></tr></tbody></table>"
        )

    def test_styled_table_colspan(self, make_doc, make_page, make_block):
        block = make_block(
            BlockType.TABLE,
            "",
            meta={
                "cells": [
                    {"text": "Wide", "row": 0, "col": 0, "colspan": 2, "rowspan": 1},
                    {"text": "A", "row": 1, "col": 0, "colspan": 1, "rowspan": 1},
                    {"text": "B", "row": 1, "col": 1, "colspan": 1, "rowspan": 1,
                     "style": {"bold": True}},
                ],
                "col_count": 2,
                "row_count": 2,
            },
        )
        html = serialize_doc(_one(make_doc, make_page, block))
        assert 'colspan="2"' in html
        assert "Wide" in html
        assert 'style="font-weight:bold"' in html

    def test_empty_document(self, make_doc):
        assert serialize_doc(make_doc()) == _wrap("")
        assert serialize_doc(UniversalDoc()) == '<article data-juldoc="1"></article>'


# ── (b) parse structure ───────────────────────────────────────


class TestParseStructure:
    def _blocks(self, inner: str) -> list[Block]:
        doc = parse_dialect(_wrap(inner))
        assert len(doc.pages) == 1
        return doc.pages[0].blocks

    def test_parse_heading(self):
        (block,) = self._blocks("<h3>Deep</h3>")
        assert block.type == BlockType.HEADING
        assert block.content == "Deep"
        assert block.meta == {"level": 3}

    def test_parse_paragraph_with_inline(self):
        (block,) = self._blocks("<p>a <em>b</em></p>")
        assert block.type == BlockType.PARAGRAPH
        assert block.content == "a <em>b</em>"

    def test_parse_paragraph_style_filtered(self):
        # CSS -> abstract dict; non-whitelisted position:absolute is dropped.
        (block,) = self._blocks('<p style="color:red; position:absolute">x</p>')
        assert block.meta == {"style": {"color": "red"}}

    def test_parse_code(self):
        (block,) = self._blocks('<pre><code class="language-py">x = 1</code></pre>')
        assert block.type == BlockType.CODE
        assert block.content == "x = 1"
        assert block.meta == {"language": "py"}

    def test_parse_code_unescapes(self):
        (block,) = self._blocks("<pre><code>&lt;div&gt;</code></pre>")
        assert block.content == "<div>"

    def test_parse_quote(self):
        (block,) = self._blocks("<blockquote>Q</blockquote>")
        assert block.type == BlockType.QUOTE
        assert block.content == "Q"

    def test_parse_list(self):
        (block,) = self._blocks("<ol><li>a</li><li>b</li></ol>")
        assert block.type == BlockType.LIST
        assert block.content == "a\nb"
        assert block.meta == {"ordered": True}

    def test_parse_image(self):
        (block,) = self._blocks('<img src="i.png" alt="I">')
        assert block.type == BlockType.IMAGE
        assert block.meta == {"src": "i.png", "alt": "I"}

    def test_parse_simple_table(self):
        (block,) = self._blocks(
            "<table><thead><tr><th>H</th></tr></thead>"
            "<tbody><tr><td>v1</td></tr><tr><td>v2</td></tr></tbody></table>"
        )
        assert block.type == BlockType.TABLE
        assert block.meta == {"headers": ["H"], "rows": [["v1"], ["v2"]]}

    def test_parse_empty_document(self):
        doc = parse_dialect(_wrap(""))
        assert doc == UniversalDoc()
        assert doc.pages == []


# ── (c) round-trip identity ───────────────────────────────────

CANONICAL_BLOCKS = [
    "<h1>Title</h1>",
    "<h2>Sub</h2>",
    "<p>plain paragraph</p>",
    '<p style="font-weight:bold; color:#ff0000">styled</p>',
    "<p>inline <strong>bold</strong> and <em>italic</em> and <u>under</u></p>",
    '<p>a <a href="page.html">link</a> here</p>',
    '<pre><code class="language-python">print(&quot;hi&quot;)</code></pre>',
    "<pre><code>&lt;raw&gt; &amp; text</code></pre>",
    "<blockquote>quoted &amp; escaped</blockquote>",
    "<ul><li>one</li><li>two</li></ul>",
    "<ol><li>first</li><li>second</li></ol>",
    '<img src="photo.png" alt="a photo">',
    "<table><thead><tr><th>Name</th><th>Age</th></tr></thead>"
    "<tbody><tr><td>Alice</td><td>30</td></tr><tr><td>Bob</td><td>25</td></tr></tbody></table>",
    '<table><tr><td colspan="2">Wide</td></tr>'
    '<tr><td>A</td><td style="font-weight:bold">B</td></tr></table>',
]


class TestRoundTrip:
    def test_serialize_parse_string_identity_each_block(self):
        for inner in CANONICAL_BLOCKS:
            html = _wrap(inner)
            assert serialize_doc(parse_dialect(html)) == html, inner

    def test_serialize_parse_string_identity_full_doc(self):
        html = _wrap("".join(CANONICAL_BLOCKS))
        assert serialize_doc(parse_dialect(html)) == html

    def test_parse_serialize_structural_identity(self, make_doc, make_page, make_block):
        blocks = [
            make_block(BlockType.HEADING, "Title", meta={"level": 1}),
            make_block(BlockType.PARAGRAPH, "plain"),
            make_block(BlockType.PARAGRAPH, "x", meta={"style": {"bold": True}}),
            make_block(BlockType.PARAGRAPH, "a <strong>b</strong>"),
            make_block(BlockType.CODE, "x = 1", meta={"language": "python"}),
            make_block(BlockType.CODE, "plain", meta={}),
            make_block(BlockType.QUOTE, "Wise"),
            make_block(BlockType.LIST, "a\nb", meta={"ordered": False}),
            make_block(BlockType.LIST, "a\nb", meta={"ordered": True}),
            make_block(BlockType.IMAGE, "", meta={"src": "i.png", "alt": "I"}),
            make_block(BlockType.TABLE, "", meta={"headers": ["H"], "rows": [["v"]]}),
            make_block(
                BlockType.TABLE,
                "",
                meta={
                    "cells": [
                        {"text": "Wide", "row": 0, "col": 0, "colspan": 2, "rowspan": 1},
                        {"text": "A", "row": 1, "col": 0, "colspan": 1, "rowspan": 1},
                        {"text": "B", "row": 1, "col": 1, "colspan": 1, "rowspan": 1,
                         "style": {"bold": True}},
                    ],
                    "col_count": 2,
                    "row_count": 2,
                },
            ),
        ]
        doc = make_doc(pages=[make_page(blocks=blocks)])
        assert parse_dialect(serialize_doc(doc)) == doc

    def test_empty_round_trip(self):
        assert parse_dialect(serialize_doc(UniversalDoc())) == UniversalDoc()


# ── (d) sanitize ──────────────────────────────────────────────


class TestSanitize:
    def test_script_removed_with_content(self):
        doc = parse_dialect(_wrap("<p>hi<script>alert(1)</script></p>"))
        block = doc.pages[0].blocks[0]
        assert block.content == "hi"
        assert "alert" not in block.content

    def test_top_level_script_dropped(self):
        doc = parse_dialect(_wrap("<script>evil()</script><p>ok</p>"))
        assert len(doc.pages[0].blocks) == 1
        assert doc.pages[0].blocks[0].content == "ok"

    def test_javascript_href_rejected(self):
        doc = parse_dialect(_wrap('<p><a href="javascript:alert(1)">x</a></p>'))
        block = doc.pages[0].blocks[0]
        assert block.content == "<a>x</a>"
        assert "javascript" not in serialize_doc(doc)

    def test_relative_and_http_href_kept(self):
        doc = parse_dialect(_wrap('<p><a href="http://ok.com/">a</a><a href="/rel">b</a></p>'))
        content = doc.pages[0].blocks[0].content
        assert 'href="http://ok.com/"' in content
        assert 'href="/rel"' in content

    def test_unknown_block_tag_unwrapped(self):
        doc = parse_dialect(_wrap("<div><p>kept</p></div>"))
        blocks = doc.pages[0].blocks
        assert len(blocks) == 1
        assert blocks[0].type == BlockType.PARAGRAPH
        assert blocks[0].content == "kept"

    def test_unknown_inline_tag_unwrapped(self):
        doc = parse_dialect(_wrap("<p>a <span>b</span> c</p>"))
        assert doc.pages[0].blocks[0].content == "a b c"

    def test_javascript_img_src_rejected(self):
        doc = parse_dialect(_wrap('<img src="javascript:alert(1)" alt="x">'))
        block = doc.pages[0].blocks[0]
        assert block.meta["src"] == ""

    def test_dangerous_style_property_dropped(self):
        doc = parse_dialect(_wrap('<p style="color:red; position:fixed; top:0">x</p>'))
        assert doc.pages[0].blocks[0].meta == {"style": {"color": "red"}}

    def test_content_escaped_on_parse(self):
        doc = parse_dialect(_wrap("<p>a &lt; b &amp; c</p>"))
        assert doc.pages[0].blocks[0].content == "a &lt; b &amp; c"


# ── (d-2) inline alias normalization (b/i -> strong/em) ───────
# execCommand('bold'/'italic') 이 <b>/<i> 를 만드는 브라우저가 있어,
# 왕복 손실 없이 정본 인라인(strong/em)으로 *변환*되어야 한다 (단순 허용 금지).


class TestInlineAliasNormalization:
    def test_b_normalized_to_strong(self):
        doc = parse_dialect(_wrap("<p><b>bold</b></p>"))
        assert doc.pages[0].blocks[0].content == "<strong>bold</strong>"

    def test_i_normalized_to_em(self):
        doc = parse_dialect(_wrap("<p><i>italic</i></p>"))
        assert doc.pages[0].blocks[0].content == "<em>italic</em>"

    def test_execcommand_bold_output_round_trips_as_strong(self):
        # execCommand('bold') 산출물 시나리오: 에디터가 저장한 HTML 에 <b> 가 섞여 옴.
        html = _wrap("<p>앞 <b>굵게</b> 뒤 <i>기울임</i></p>")
        out = serialize_doc(parse_dialect(html))
        assert "<strong>굵게</strong>" in out
        assert "<em>기울임</em>" in out
        assert "<b>" not in out
        assert "<i>" not in out

    def test_nested_b_i_normalized(self):
        doc = parse_dialect(_wrap("<p><b><i>both</i></b></p>"))
        assert doc.pages[0].blocks[0].content == "<strong><em>both</em></strong>"

    def test_bare_top_level_b_becomes_strong_paragraph(self):
        doc = parse_dialect(_wrap("<b>loose</b>"))
        block = doc.pages[0].blocks[0]
        assert block.type == BlockType.PARAGRAPH
        assert block.content == "<strong>loose</strong>"

    def test_normalized_output_is_idempotent(self):
        once = serialize_doc(parse_dialect(_wrap("<p><b>x</b></p>")))
        twice = serialize_doc(parse_dialect(once))
        assert once == twice


# ── (e) page flattening ───────────────────────────────────────


class TestPageFlattening:
    def test_multiple_pages_flatten_on_serialize(self, make_doc, make_page, make_block):
        doc = make_doc(
            pages=[
                make_page(blocks=[make_block(BlockType.PARAGRAPH, "P1")]),
                make_page(blocks=[make_block(BlockType.PARAGRAPH, "P2")]),
            ]
        )
        assert serialize_doc(doc) == _wrap("<p>P1</p><p>P2</p>")

    def test_parse_produces_single_page(self, make_doc, make_page, make_block):
        doc = make_doc(
            pages=[
                make_page(blocks=[make_block(BlockType.PARAGRAPH, "P1")]),
                make_page(blocks=[make_block(BlockType.PARAGRAPH, "P2")]),
            ]
        )
        reparsed = parse_dialect(serialize_doc(doc))
        assert len(reparsed.pages) == 1
        assert [b.content for b in reparsed.pages[0].blocks] == ["P1", "P2"]

    def test_round_trip_via_page_object(self):
        doc = UniversalDoc(pages=[Page(blocks=[Block(BlockType.PARAGRAPH, "x", {})])])
        assert parse_dialect(serialize_doc(doc)) == doc


# ── reference HWP: real parse -> serialize -> parse round-trip ─


@pytest.mark.skipif(not REFERENCE_HWP.exists(), reason="reference HWP not available")
class TestReferenceHWPRoundTrip:
    """serialize_doc must handle the real HWP parser output (abstract-dict
    styles, styled tables with per-cell dict styles) without crashing, and the
    dialect form must be idempotent under a serialize -> parse -> serialize cycle.
    """

    def _doc(self):
        from src.engine.doc.parsers.hwp import HWPParser

        return HWPParser().parse_bytes(REFERENCE_HWP.read_bytes())

    def test_serialize_does_not_crash_and_is_wrapped(self):
        html = serialize_doc(self._doc())
        assert html.startswith('<article data-juldoc="1">')
        assert html.endswith("</article>")

    def test_parse_dialect_of_serialized_is_universaldoc(self):
        html = serialize_doc(self._doc())
        reparsed = parse_dialect(html)
        assert isinstance(reparsed, UniversalDoc)
        assert len(reparsed.pages) == 1

    def test_serialize_parse_serialize_is_idempotent(self):
        html1 = serialize_doc(self._doc())
        html2 = serialize_doc(parse_dialect(html1))
        assert html1 == html2

    def test_serialized_contains_reference_content(self):
        html = serialize_doc(self._doc())
        assert "박연미" in html


# ── style codec (abstract dict <-> CSS) ───────────────────────


class TestStyleCodec:
    def test_abstract_dict_round_trips_through_css(self):
        # Every emitted property survives dict -> CSS -> dict unchanged.
        style = {
            "font": "Arial",
            "size": 12.0,
            "bold": True,
            "italic": True,
            "underline": True,
            "color": "#ff0000",
            "align": "center",
            "line_spacing": 160,
        }
        assert css_to_style(style_to_css(style)) == style

    def test_non_whitelisted_css_dropped_on_reverse(self):
        assert css_to_style("color:red; position:absolute; z-index:5") == {"color": "red"}

    def test_style_to_css_omits_black_and_falsey(self):
        assert style_to_css({"bold": False, "color": "#000000"}) == ""

    def test_css_to_style_drops_dangerous_values(self):
        assert css_to_style("font-family:url(x); color:red") == {"color": "red"}

    def test_hwp_shape_size_align_line_spacing(self):
        style = {"size": 10.0, "align": "justify", "line_spacing": 160, "color": "#123456"}
        assert css_to_style(style_to_css(style)) == style
