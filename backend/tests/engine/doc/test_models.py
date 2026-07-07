"""Tests for UniversalDoc data structures (models.py).

Verifies the Document → Page → Block hierarchy,
BlockType enum, and dataclass behavior.
"""
from __future__ import annotations

# ── BlockType enum ──────────────────────────────────────────────


class TestBlockType:
    def test_all_expected_types_exist(self):
        from src.engine.doc.models import BlockType

        expected = {"HEADING", "PARAGRAPH", "CODE", "IMAGE", "QUOTE", "LIST", "TABLE"}
        actual = {bt.value for bt in BlockType}
        assert expected == actual

    def test_is_str_enum(self):
        from src.engine.doc.models import BlockType

        assert isinstance(BlockType.HEADING, str)
        assert BlockType.HEADING == "HEADING"

    def test_block_type_used_as_dict_key(self):
        from src.engine.doc.models import BlockType

        d = {BlockType.HEADING: 1}
        assert d["HEADING"] == 1


# ── Block ───────────────────────────────────────────────────────


class TestBlock:
    def test_create_paragraph_block(self, make_block):
        from src.engine.doc.models import BlockType

        block = make_block(BlockType.PARAGRAPH, "Hello world")
        assert block.type == BlockType.PARAGRAPH
        assert block.content == "Hello world"
        assert block.meta == {}

    def test_create_heading_with_level(self, make_block):
        from src.engine.doc.models import BlockType

        block = make_block(BlockType.HEADING, "Title", meta={"level": 1})
        assert block.meta["level"] == 1

    def test_create_code_with_language(self, make_block):
        from src.engine.doc.models import BlockType

        block = make_block(BlockType.CODE, "print('hi')", meta={"language": "python"})
        assert block.meta["language"] == "python"

    def test_create_image_with_src_and_alt(self, make_block):
        from src.engine.doc.models import BlockType

        block = make_block(BlockType.IMAGE, "", meta={"src": "img.png", "alt": "photo"})
        assert block.meta["src"] == "img.png"
        assert block.meta["alt"] == "photo"

    def test_create_list_ordered(self, make_block):
        from src.engine.doc.models import BlockType

        block = make_block(BlockType.LIST, "a\nb", meta={"ordered": True})
        assert block.meta["ordered"] is True

    def test_create_list_unordered(self, make_block):
        from src.engine.doc.models import BlockType

        block = make_block(BlockType.LIST, "x\ny", meta={"ordered": False})
        assert block.meta["ordered"] is False

    def test_create_table_with_headers_and_rows(self, make_block):
        from src.engine.doc.models import BlockType

        block = make_block(
            BlockType.TABLE,
            "",
            meta={
                "headers": ["Name", "Age"],
                "rows": [["Alice", "30"], ["Bob", "25"]],
            },
        )
        assert block.meta["headers"] == ["Name", "Age"]
        assert len(block.meta["rows"]) == 2

    def test_create_quote_block(self, make_block):
        from src.engine.doc.models import BlockType

        block = make_block(BlockType.QUOTE, "To be or not to be")
        assert block.type == BlockType.QUOTE

    def test_meta_defaults_to_empty_dict(self):
        from src.engine.doc.models import Block, BlockType

        block = Block(type=BlockType.PARAGRAPH, content="text")
        assert block.meta == {}

    def test_two_blocks_with_same_values_are_equal(self):
        from src.engine.doc.models import Block, BlockType

        a = Block(type=BlockType.PARAGRAPH, content="x")
        b = Block(type=BlockType.PARAGRAPH, content="x")
        assert a == b

    def test_blocks_do_not_share_meta_dict(self):
        from src.engine.doc.models import Block, BlockType

        a = Block(type=BlockType.PARAGRAPH, content="x")
        b = Block(type=BlockType.PARAGRAPH, content="x")
        a.meta["key"] = "val"
        assert "key" not in b.meta


# ── Page ────────────────────────────────────────────────────────


class TestPage:
    def test_empty_page(self, make_page):
        page = make_page()
        assert page.blocks == []

    def test_page_with_blocks(self, make_block, make_page):
        from src.engine.doc.models import BlockType

        blocks = [
            make_block(BlockType.HEADING, "Title", meta={"level": 1}),
            make_block(BlockType.PARAGRAPH, "Body text"),
        ]
        page = make_page(blocks)
        assert len(page.blocks) == 2
        assert page.blocks[0].type == BlockType.HEADING

    def test_block_order_preserved(self, make_block, make_page):
        from src.engine.doc.models import BlockType

        blocks = [
            make_block(BlockType.PARAGRAPH, "first"),
            make_block(BlockType.PARAGRAPH, "second"),
            make_block(BlockType.PARAGRAPH, "third"),
        ]
        page = make_page(blocks)
        contents = [b.content for b in page.blocks]
        assert contents == ["first", "second", "third"]

    def test_pages_do_not_share_block_lists(self, make_page):
        a = make_page()
        b = make_page()
        from src.engine.doc.models import Block, BlockType

        a.blocks.append(Block(type=BlockType.PARAGRAPH, content="x"))
        assert len(b.blocks) == 0


# ── UniversalDoc ────────────────────────────────────────────────


class TestUniversalDoc:
    def test_empty_doc(self, make_doc):
        doc = make_doc()
        assert doc.pages == []
        assert doc.metadata == {}

    def test_doc_with_metadata(self, make_doc):
        doc = make_doc(metadata={"title": "My Doc", "author": "Alice"})
        assert doc.metadata["title"] == "My Doc"
        assert doc.metadata["author"] == "Alice"

    def test_doc_with_pages(self, make_page, make_block, make_doc):
        from src.engine.doc.models import BlockType

        page = make_page([make_block(BlockType.PARAGRAPH, "content")])
        doc = make_doc(pages=[page])
        assert len(doc.pages) == 1
        assert doc.pages[0].blocks[0].content == "content"

    def test_multi_page_doc(self, make_page, make_block, make_doc):
        from src.engine.doc.models import BlockType

        pages = [
            make_page([make_block(BlockType.HEADING, "Page 1", meta={"level": 1})]),
            make_page([make_block(BlockType.HEADING, "Page 2", meta={"level": 1})]),
        ]
        doc = make_doc(pages=pages)
        assert len(doc.pages) == 2

    def test_docs_do_not_share_pages_list(self, make_doc):
        a = make_doc()
        b = make_doc()
        from src.engine.doc.models import Page

        a.pages.append(Page())
        assert len(b.pages) == 0

    def test_docs_do_not_share_metadata_dict(self, make_doc):
        a = make_doc()
        b = make_doc()
        a.metadata["key"] = "val"
        assert "key" not in b.metadata
