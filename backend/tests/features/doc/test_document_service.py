"""DocumentService 유스케이스 테스트 — InMemory repo, 반환값·관측 상태로 검증. (juldoc 이식)

asyncio_mode=auto 라 async 테스트 함수를 그대로 쓴다(juldoc 의 asyncio.run 래퍼 불필요).
"""
import io
import uuid
import zipfile

import pytest
from src.features.doc.application.document_service import DocumentService
from src.features.doc.domain.models import (
    CannotDetectFormat,
    DocumentNotFound,
    UnsupportedDocumentFormat,
)

from tests.fixtures.fake_doc_repo import FakeDocumentRepo


@pytest.fixture
def service() -> DocumentService:
    return DocumentService(FakeDocumentRepo())


class TestUpload:
    async def test_upload_markdown_renders_canonical_html(self, service):
        doc = await service.upload_document("note.md", b"# Title\n\nBody\n")
        assert doc.title == "note"
        assert doc.format == "md"
        assert "<h1>Title</h1>" in doc.html
        assert "<p>Body</p>" in doc.html

    async def test_upload_computes_source_hash(self, service):
        doc = await service.upload_document("a.txt", b"hello")
        assert doc.source_hash == (
            "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
        )

    async def test_upload_no_extension_raises(self, service):
        with pytest.raises(CannotDetectFormat) as ei:
            await service.upload_document("noext", b"data")
        assert ei.value.status_code == 422

    async def test_upload_unsupported_format_raises_400(self, service):
        with pytest.raises(UnsupportedDocumentFormat) as ei:
            await service.upload_document("doc.zzz", b"data")
        assert ei.value.status_code == 400

    async def test_upload_persists_and_is_retrievable(self, service):
        created = await service.upload_document("x.md", b"# Hi")
        fetched = await service.get_document(created.id)
        assert fetched.id == created.id
        assert fetched.html == created.html


class TestCreateEmpty:
    async def test_create_empty_has_canonical_empty_html(self, service):
        doc = await service.create_empty("My Doc")
        assert doc.title == "My Doc"
        assert doc.html == '<article data-juldoc="1"></article>'

    async def test_create_empty_default_title(self, service):
        doc = await service.create_empty("")
        assert doc.title == "Untitled"


class TestGet:
    async def test_get_missing_raises_not_found(self, service):
        with pytest.raises(DocumentNotFound) as ei:
            await service.get_document(uuid.uuid4())
        assert ei.value.status_code == 404


class TestSaveHtml:
    async def test_save_html_normalizes_to_canonical(self, service):
        doc = await service.create_empty("D")
        updated = await service.save_html(doc.id, "<p>edited</p>")
        assert updated.html == '<article data-juldoc="1"><p>edited</p></article>'
        assert await service.get_html(doc.id) == updated.html

    async def test_save_html_sanitizes_stored_xss(self, service):
        doc = await service.create_empty("D")
        payload = '<p>hi</p><img src=x onerror="alert(1)"><script>alert(2)</script>'
        updated = await service.save_html(doc.id, payload)
        assert "onerror" not in updated.html
        assert "<script" not in updated.html
        assert "alert(1)" not in updated.html
        assert "alert(2)" not in updated.html
        assert "<p>hi</p>" in updated.html

    async def test_save_html_missing_raises_not_found(self, service):
        with pytest.raises(DocumentNotFound):
            await service.save_html(uuid.uuid4(), "<p>x</p>")


class TestList:
    async def test_list_returns_items_and_total(self, service):
        for i in range(3):
            await service.create_empty(f"doc-{i}")
        items, total = await service.list_documents(page=1, page_size=2)
        assert total == 3
        assert len(items) == 2

    async def test_list_excludes_soft_deleted(self, service):
        a = await service.create_empty("a")
        await service.create_empty("b")
        await service.delete_document(a.id)
        items, total = await service.list_documents(page=1, page_size=10)
        assert total == 1
        assert all(d.id != a.id for d in items)


class TestDelete:
    async def test_delete_makes_document_unreachable(self, service):
        doc = await service.create_empty("gone")
        await service.delete_document(doc.id)
        with pytest.raises(DocumentNotFound):
            await service.get_document(doc.id)

    async def test_delete_missing_raises_not_found(self, service):
        with pytest.raises(DocumentNotFound):
            await service.delete_document(uuid.uuid4())

    async def test_delete_twice_raises_not_found(self, service):
        doc = await service.create_empty("twice")
        await service.delete_document(doc.id)
        with pytest.raises(DocumentNotFound):
            await service.delete_document(doc.id)


class TestExportEpub:
    async def test_export_returns_title_and_epub_bytes(self, service):
        doc = await service.upload_document("note.md", b"# Title\n\nBody\n")
        title, data = await service.export_epub(doc.id)
        assert title == "note"
        assert data[:2] == b"PK"

    async def test_export_roundtrips_canonical_content(self, service):
        doc = await service.create_empty("t")
        await service.save_html(doc.id, "<h1>Heading</h1><p>hello <strong>bold</strong></p>")
        _title, data = await service.export_epub(doc.id)
        zf = zipfile.ZipFile(io.BytesIO(data))
        content = zf.read("OEBPS/content.xhtml").decode()
        assert "<h1" in content
        assert "<strong>bold</strong>" in content

    async def test_export_missing_document_raises_not_found(self, service):
        with pytest.raises(DocumentNotFound):
            await service.export_epub(uuid.uuid4())


class _StubStorage:
    """StorageAdapter 최소 스텁 — 수출 이미지 resolve 경로만 구동한다."""

    def __init__(self, objects: dict[str, bytes]) -> None:
        self._objects = objects

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        self._objects[key] = data

    async def get(self, key: str) -> bytes | None:
        return self._objects.get(key)

    def url_for(self, key: str) -> str:
        return f"/media/{key}"

    async def exists(self, key: str) -> bool:
        return key in self._objects


_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16


def _service_with(objects: dict[str, bytes]) -> DocumentService:
    return DocumentService(FakeDocumentRepo(), _StubStorage(objects))


def _read(data: bytes) -> zipfile.ZipFile:
    return zipfile.ZipFile(io.BytesIO(data))


class TestExportImageResolution:
    """service 가 정본 img '/media/{key}' → storage.get 로 바이트 resolve 해 임베드한다."""

    async def _doc_with_image(self, svc: DocumentService):
        doc = await svc.create_empty("Img")
        await svc.save_html(doc.id, '<p>hi</p><img src="/media/photo.png" alt="pic">')
        return doc

    async def test_docx_embeds_resolved_image(self):
        svc = _service_with({"photo.png": _PNG})
        doc = await self._doc_with_image(svc)
        _title, data = await svc.export_docx(doc.id)
        zf = _read(data)
        assert "word/media/image1.png" in zf.namelist()
        assert zf.read("word/media/image1.png") == _PNG

    async def test_epub_embeds_resolved_image(self):
        svc = _service_with({"photo.png": _PNG})
        doc = await self._doc_with_image(svc)
        _title, data = await svc.export_epub(doc.id)
        zf = _read(data)
        assert "OEBPS/images/image1.png" in zf.namelist()

    async def test_missing_key_falls_back_to_alt_and_export_succeeds(self):
        svc = _service_with({})  # 빈 저장소
        doc = await self._doc_with_image(svc)
        title, data = await svc.export_docx(doc.id)
        assert title == "Img"
        assert data[:2] == b"PK"
        zf = _read(data)
        assert not any(n.startswith("word/media/") for n in zf.namelist())
        assert "pic" in zf.read("word/document.xml").decode()  # alt 텍스트 폴백

    async def test_no_storage_falls_back_to_alt(self):
        svc = DocumentService(FakeDocumentRepo())
        doc = await self._doc_with_image(svc)
        _title, data = await svc.export_epub(doc.id)
        zf = _read(data)
        assert not any(n.startswith("OEBPS/images/") for n in zf.namelist())


class TestExportDocx:
    async def test_export_returns_title_and_docx_bytes(self, service):
        doc = await service.upload_document("note.md", b"# Title\n\nBody\n")
        title, data = await service.export_docx(doc.id)
        assert title == "note"
        assert data[:2] == b"PK"

    async def test_export_roundtrips_canonical_content(self, service):
        doc = await service.create_empty("t")
        await service.save_html(doc.id, "<h1>Heading</h1><p>hi <strong>bold</strong></p>")
        _title, data = await service.export_docx(doc.id)
        document = _read(data).read("word/document.xml").decode()
        assert '<w:pStyle w:val="Heading1"/>' in document
        assert "<w:b/>" in document

    async def test_export_missing_document_raises_not_found(self, service):
        with pytest.raises(DocumentNotFound):
            await service.export_docx(uuid.uuid4())
