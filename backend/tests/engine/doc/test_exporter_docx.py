"""DOCX exporter unit tests (exporters/docx.py).

산출 bytes 를 zipfile 로 열어 OOXML 필수 파트·모든 XML 파트의 유효성·방언 블록별
매핑(heading pStyle/para run 서식/list numPr/code/table gridSpan·vMerge)·이미지 임베드
(word/media + document.xml.rels 관계)를 실측 검증한다. 순수 stdlib(zipfile/xml.etree)로만
확인 — 실제 Word 없이 XML 파싱 + 구조 검증.
"""
from __future__ import annotations

import io
import struct
import xml.etree.ElementTree as ET
import zipfile

import pytest
from src.engine.doc.exporters import export_docx
from src.engine.doc.models import Block, BlockType, Page, UniversalDoc

_XML_PARTS = (
    "[Content_Types].xml",
    "_rels/.rels",
    "docProps/core.xml",
    "word/document.xml",
    "word/_rels/document.xml.rels",
    "word/styles.xml",
    "word/numbering.xml",
)


def _png_bytes(w: int = 2, h: int = 3) -> bytes:
    """스니핑 가능한 최소 PNG(시그니처 + IHDR 치수). 저장/임베드 검증용(디코드 불요)."""
    sig = b"\x89PNG\r\n\x1a\n"
    length = struct.pack(">I", 13)
    ihdr = b"IHDR" + struct.pack(">II", w, h) + b"\x08\x06\x00\x00\x00"
    crc = b"\x00\x00\x00\x00"
    return sig + length + ihdr + crc + b"\x00" * 8


def _seven_block_doc() -> UniversalDoc:
    blocks = [
        Block(BlockType.HEADING, "Main <strong>Title</strong>", {"level": 1}),
        Block(BlockType.PARAGRAPH, "a <strong>b</strong> & c", {"style": {"align": "center"}}),
        Block(BlockType.CODE, "x = 1 < 2 & 3", {"language": "python"}),
        Block(BlockType.QUOTE, "Wise & quoted <em>words</em>"),
        Block(BlockType.LIST, "one\ntwo", {"ordered": True}),
        Block(BlockType.IMAGE, "", {"src": "/media/photo.png", "alt": "A & photo"}),
        Block(BlockType.TABLE, "", {"headers": ["Name", "Age"], "rows": [["Alice", "30"]]}),
    ]
    return UniversalDoc(pages=[Page(blocks=blocks)])


@pytest.fixture
def docx_bytes() -> bytes:
    return export_docx(_seven_block_doc(), "한글 제목 & Test")


@pytest.fixture
def zf(docx_bytes) -> zipfile.ZipFile:
    return zipfile.ZipFile(io.BytesIO(docx_bytes))


class TestPackage:
    def test_returns_bytes_with_zip_magic(self, docx_bytes):
        assert isinstance(docx_bytes, bytes)
        assert docx_bytes[:2] == b"PK"

    def test_required_parts_present(self, zf):
        names = set(zf.namelist())
        for part in _XML_PARTS:
            assert part in names

    def test_all_xml_parts_are_well_formed(self, zf):
        for part in _XML_PARTS:
            ET.fromstring(zf.read(part))  # raises on invalid XML

    def test_content_types_declares_document_and_images(self, zf):
        ct = zf.read("[Content_Types].xml").decode()
        assert "/word/document.xml" in ct
        assert "wordprocessingml.document.main+xml" in ct
        assert 'Extension="png"' in ct
        assert 'Extension="webp"' in ct

    def test_root_rels_point_to_document(self, zf):
        rels = zf.read("_rels/.rels").decode()
        assert "word/document.xml" in rels
        assert "docProps/core.xml" in rels

    def test_core_has_escaped_title(self, zf):
        core = zf.read("docProps/core.xml").decode()
        assert "한글 제목" in core
        assert "&amp;" in core  # & 이스케이프(유효 XML)


class TestBlockMapping:
    def _doc(self, zf) -> str:
        return zf.read("word/document.xml").decode()

    def test_heading_uses_pstyle(self, zf):
        assert '<w:pStyle w:val="Heading1"/>' in self._doc(zf)

    def test_inline_strong_becomes_bold_run(self, zf):
        doc = self._doc(zf)
        assert "<w:b/>" in doc
        assert "<w:t xml:space=\"preserve\">Title</w:t>" in doc

    def test_paragraph_align_maps_to_jc(self, zf):
        assert '<w:jc w:val="center"/>' in self._doc(zf)

    def test_text_is_xml_escaped(self, zf):
        assert "1 &lt; 2 &amp; 3" in self._doc(zf)  # 코드 본문 이스케이프

    def test_code_uses_pstyle(self, zf):
        assert '<w:pStyle w:val="Code"/>' in self._doc(zf)

    def test_quote_uses_pstyle(self, zf):
        assert '<w:pStyle w:val="Quote"/>' in self._doc(zf)

    def test_list_uses_numpr(self, zf):
        doc = self._doc(zf)
        assert "<w:numPr>" in doc
        assert '<w:numId w:val="2"/>' in doc  # ordered → decimal(numId 2)

    def test_numbering_defines_bullet_and_decimal(self, zf):
        numbering = zf.read("word/numbering.xml").decode()
        assert 'w:val="bullet"' in numbering
        assert 'w:val="decimal"' in numbering

    def test_simple_table_renders_tbl(self, zf):
        doc = self._doc(zf)
        assert "<w:tbl>" in doc
        assert "Alice" in doc
        assert "Name" in doc

    def test_image_without_bytes_falls_back_to_alt(self, zf):
        # images 미제공 → alt 텍스트 문단, media/drawing 없음.
        doc = self._doc(zf)
        assert "A &amp; photo" in doc
        assert "<w:drawing>" not in doc
        assert not any(n.startswith("word/media/") for n in zf.namelist())


class TestImageEmbed:
    def _export_with_image(self) -> zipfile.ZipFile:
        doc = UniversalDoc(pages=[Page(blocks=[
            Block(BlockType.IMAGE, "", {"src": "/media/photo.png", "alt": "pic"}),
        ])])
        data = export_docx(doc, "with-image", {"/media/photo.png": _png_bytes(2, 3)})
        return zipfile.ZipFile(io.BytesIO(data))

    def test_media_part_written(self):
        zf = self._export_with_image()
        assert "word/media/image1.png" in zf.namelist()
        assert zf.read("word/media/image1.png") == _png_bytes(2, 3)

    def test_document_has_drawing_and_embed(self):
        zf = self._export_with_image()
        doc = zf.read("word/document.xml").decode()
        assert "<w:drawing>" in doc
        assert 'r:embed="rIdImg1"' in doc

    def test_rels_declares_image_relationship(self):
        zf = self._export_with_image()
        rels = zf.read("word/_rels/document.xml.rels").decode()
        assert 'Id="rIdImg1"' in rels
        assert "media/image1.png" in rels

    def test_extent_reflects_sniffed_dimensions(self):
        # 2x3 px → EMU(px*9525). 본문 폭 상한 미만이므로 그대로.
        zf = self._export_with_image()
        doc = zf.read("word/document.xml").decode()
        assert f'cx="{2 * 9525}"' in doc
        assert f'cy="{3 * 9525}"' in doc

    def test_unknown_format_falls_back_to_alt(self):
        doc = UniversalDoc(pages=[Page(blocks=[
            Block(BlockType.IMAGE, "", {"src": "/media/x", "alt": "fallback"}),
        ])])
        data = export_docx(doc, "t", {"/media/x": b"not an image"})
        zf = zipfile.ZipFile(io.BytesIO(data))
        assert "<w:drawing>" not in zf.read("word/document.xml").decode()
        assert not any(n.startswith("word/media/") for n in zf.namelist())


class TestTableSpans:
    def test_colspan_maps_to_gridspan(self):
        cells = [
            {"text": "wide", "row": 0, "col": 0, "colspan": 2, "rowspan": 1},
            {"text": "a", "row": 1, "col": 0, "colspan": 1, "rowspan": 1},
            {"text": "b", "row": 1, "col": 1, "colspan": 1, "rowspan": 1},
        ]
        doc = UniversalDoc(pages=[Page(blocks=[
            Block(BlockType.TABLE, "", {"cells": cells, "row_count": 2, "col_count": 2}),
        ])])
        xml = zipfile.ZipFile(io.BytesIO(export_docx(doc, "t"))).read(
            "word/document.xml"
        ).decode()
        ET.fromstring(xml)  # 유효 XML
        assert '<w:gridSpan w:val="2"/>' in xml

    def test_rowspan_maps_to_vmerge_restart_and_continue(self):
        cells = [
            {"text": "tall", "row": 0, "col": 0, "colspan": 1, "rowspan": 2,
             "style": {"bold": True}},
            {"text": "top", "row": 0, "col": 1, "colspan": 1, "rowspan": 1},
            {"text": "bot", "row": 1, "col": 1, "colspan": 1, "rowspan": 1},
        ]
        doc = UniversalDoc(pages=[Page(blocks=[
            Block(BlockType.TABLE, "", {"cells": cells, "row_count": 2, "col_count": 2}),
        ])])
        xml = zipfile.ZipFile(io.BytesIO(export_docx(doc, "t"))).read(
            "word/document.xml"
        ).decode()
        ET.fromstring(xml)
        assert '<w:vMerge w:val="restart"/>' in xml  # 시작 셀
        assert "<w:vMerge/>" in xml  # 연속 셀
        assert "<w:b/>" in xml  # 셀 스타일 bold → run 서식


def test_empty_doc_is_valid_docx():
    data = export_docx(UniversalDoc(), "Empty")
    zf = zipfile.ZipFile(io.BytesIO(data))
    for part in _XML_PARTS:
        ET.fromstring(zf.read(part))  # 빈 문서도 유효 패키지
