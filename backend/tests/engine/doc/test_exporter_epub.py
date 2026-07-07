"""EPUB exporter unit tests (exporters/epub.py).

산출 bytes 를 zipfile 로 열어 OCF 규약(mimetype 첫 엔트리·무압축)·필수 엔트리·
모든 XHTML 의 XML 유효성·헤딩 앵커 목차·방언 7블록 변환을 실측 검증한다.
순수 stdlib(zipfile/xml.etree) 로만 확인 — 외부 EPUB 리더 없이.
"""
from __future__ import annotations

import io
import xml.etree.ElementTree as ET
import zipfile

import pytest
from src.engine.doc.exporters import export_epub
from src.engine.doc.models import Block, BlockType, Page, UniversalDoc

_XML_ENTRIES = (
    "META-INF/container.xml",
    "OEBPS/content.opf",
    "OEBPS/nav.xhtml",
    "OEBPS/content.xhtml",
)


def _seven_block_doc() -> UniversalDoc:
    """방언 7블록 전부(HEADING/PARAGRAPH/CODE/QUOTE/LIST/IMAGE/TABLE)를 담은 문서."""
    blocks = [
        Block(BlockType.HEADING, "Main <strong>Title</strong>", {"level": 1}),
        Block(BlockType.PARAGRAPH, "a <strong>b</strong> & c", {"style": {"bold": True}}),
        Block(BlockType.CODE, "x = 1 < 2 & 3", {"language": "python"}),
        Block(BlockType.QUOTE, "Wise & quoted <em>words</em>"),
        Block(BlockType.LIST, "one\ntwo", {"ordered": True}),
        Block(BlockType.IMAGE, "", {"src": "photo.png", "alt": "A & photo"}),
        Block(BlockType.TABLE, "", {"headers": ["Name", "Age"], "rows": [["Alice", "30"]]}),
    ]
    return UniversalDoc(pages=[Page(blocks=blocks)])


@pytest.fixture
def epub_bytes() -> bytes:
    return export_epub(_seven_block_doc(), "한글 제목 & Test")


@pytest.fixture
def zf(epub_bytes) -> zipfile.ZipFile:
    return zipfile.ZipFile(io.BytesIO(epub_bytes))


class TestOcfContainer:
    def test_returns_bytes_with_zip_magic(self, epub_bytes):
        assert isinstance(epub_bytes, bytes)
        assert epub_bytes[:2] == b"PK"

    def test_mimetype_is_first_entry(self, zf):
        assert zf.namelist()[0] == "mimetype"

    def test_mimetype_is_stored_uncompressed(self, zf):
        info = zf.infolist()[0]
        assert info.compress_type == zipfile.ZIP_STORED
        assert zf.read("mimetype") == b"application/epub+zip"

    def test_required_entries_present(self, zf):
        names = set(zf.namelist())
        for entry in _XML_ENTRIES:
            assert entry in names


class TestXmlValidity:
    def test_all_xml_entries_parse(self, zf):
        # 모든 xhtml/opf/container 가 well-formed XML 이어야 한다.
        for entry in _XML_ENTRIES:
            ET.fromstring(zf.read(entry))  # raises on invalid XML

    def test_opf_has_title_identifier_language(self, zf):
        opf = zf.read("OEBPS/content.opf").decode()
        assert "urn:uuid:" in opf
        assert "<dc:language>ko</dc:language>" in opf
        assert "한글 제목" in opf  # dc:title 에 원제목(이스케이프 후)이 들어간다
        assert "&amp;" in opf  # & 이스케이프

    def test_content_xhtml_default_namespace(self, zf):
        content = zf.read("OEBPS/content.xhtml").decode()
        assert 'xmlns="http://www.w3.org/1999/xhtml"' in content


class TestNavToc:
    def test_headings_appear_as_anchors(self, zf):
        nav = zf.read("OEBPS/nav.xhtml").decode()
        content = zf.read("OEBPS/content.xhtml").decode()
        # h1 이 nav 에 앵커로 등장하고, 같은 앵커 id 가 본문 헤딩에 존재.
        assert 'href="content.xhtml#sec1"' in nav
        assert 'id="sec1"' in content
        assert "Title" in nav  # 헤딩 텍스트가 목차 라벨에 나타남

    def test_empty_doc_has_fallback_toc_and_valid_xml(self):
        data = export_epub(UniversalDoc(), "Empty")
        z = zipfile.ZipFile(io.BytesIO(data))
        for entry in _XML_ENTRIES:
            ET.fromstring(z.read(entry))  # 여전히 유효
        nav = z.read("OEBPS/nav.xhtml").decode()
        assert 'href="content.xhtml"' in nav  # 헤딩 없어도 폴백 링크 1개


class TestSevenBlockConversion:
    """방언 7블록이 각각 유효 XHTML 로 변환되는지 본문에서 확인."""

    def test_heading(self, zf):
        assert "<h1" in zf.read("OEBPS/content.xhtml").decode()

    def test_paragraph_with_style(self, zf):
        content = zf.read("OEBPS/content.xhtml").decode()
        assert "<p style=" in content
        assert "font-weight:bold" in content

    def test_code(self, zf):
        content = zf.read("OEBPS/content.xhtml").decode()
        assert '<pre><code class="language-python">' in content
        assert "x = 1 &lt; 2 &amp; 3" in content  # 코드 본문 이스케이프

    def test_quote(self, zf):
        assert "<blockquote>" in zf.read("OEBPS/content.xhtml").decode()

    def test_list_ordered(self, zf):
        content = zf.read("OEBPS/content.xhtml").decode()
        assert "<ol>" in content
        assert "<li>one</li>" in content

    def test_image_becomes_alt_text_no_binary(self, zf):
        # v1: img 태그·바이너리 자산 없음 — alt 텍스트만 남는다.
        content = zf.read("OEBPS/content.xhtml").decode()
        assert "juldoc-image" in content
        assert "A &amp; photo" in content
        assert "<img" not in content
        assert "photo.png" not in content

    def test_table(self, zf):
        content = zf.read("OEBPS/content.xhtml").decode()
        assert "<table>" in content
        assert "<th>Name</th>" in content
        assert "<td>Alice</td>" in content

    def test_inline_markup_preserved_and_escaped(self, zf):
        content = zf.read("OEBPS/content.xhtml").decode()
        assert "<strong>Title</strong>" in content  # 인라인 화이트리스트 유지
        assert "&amp;" in content  # & 이스케이프(유효 XML)


def _png_bytes() -> bytes:
    """스니핑 가능한 최소 PNG(시그니처 기반). 임베드 검증용(디코드 불요)."""
    return b"\x89PNG\r\n\x1a\n" + b"\x00" * 16


def _webp_bytes() -> bytes:
    return b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"VP8 " + b"\x00" * 20


def _image_doc(src: str = "/media/photo.png") -> UniversalDoc:
    blocks = [Block(BlockType.IMAGE, "", {"src": src, "alt": "A & photo"})]
    return UniversalDoc(pages=[Page(blocks=blocks)])


class TestImageEmbed:
    """images 매핑을 주면 OEBPS/images 임베드 + OPF manifest 등록, 없으면 alt 폴백."""

    def _zf(self, doc: UniversalDoc, images=None) -> zipfile.ZipFile:
        return zipfile.ZipFile(io.BytesIO(export_epub(doc, "T", images)))

    def test_image_embedded_into_oebps_images(self):
        zf = self._zf(_image_doc(), {"/media/photo.png": _png_bytes()})
        assert "OEBPS/images/image1.png" in zf.namelist()
        assert zf.read("OEBPS/images/image1.png") == _png_bytes()

    def test_content_references_relative_img(self):
        zf = self._zf(_image_doc(), {"/media/photo.png": _png_bytes()})
        content = zf.read("OEBPS/content.xhtml").decode()
        assert '<img src="images/image1.png"' in content
        assert 'alt="A &amp; photo"' in content
        assert "juldoc-image" not in content  # alt 폴백 아님

    def test_manifest_registers_image_with_media_type(self):
        zf = self._zf(_image_doc(), {"/media/photo.png": _png_bytes()})
        opf = zf.read("OEBPS/content.opf").decode()
        assert 'href="images/image1.png"' in opf
        assert 'media-type="image/png"' in opf

    def test_webp_media_type_reflected(self):
        zf = self._zf(_image_doc("/media/x.webp"), {"/media/x.webp": _webp_bytes()})
        opf = zf.read("OEBPS/content.opf").decode()
        assert 'media-type="image/webp"' in opf
        assert "OEBPS/images/image1.webp" in zf.namelist()

    def test_missing_mapping_falls_back_to_alt(self):
        # images 자체가 없으면(None) 종전대로 alt 문단 — 임베드/manifest 없음.
        zf = self._zf(_image_doc())
        content = zf.read("OEBPS/content.xhtml").decode()
        assert "juldoc-image" in content
        assert "<img" not in content
        assert not any(n.startswith("OEBPS/images/") for n in zf.namelist())

    def test_unknown_format_falls_back_to_alt(self):
        zf = self._zf(_image_doc(), {"/media/photo.png": b"not an image"})
        content = zf.read("OEBPS/content.xhtml").decode()
        assert "juldoc-image" in content
        assert "<img" not in content

    def test_all_xml_still_valid_with_embed(self):
        zf = self._zf(_image_doc(), {"/media/photo.png": _png_bytes()})
        for entry in _XML_ENTRIES:
            ET.fromstring(zf.read(entry))
