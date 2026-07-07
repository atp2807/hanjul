"""문서 유스케이스 계층 — repo Protocol + StorageAdapter 에만 의존. (juldoc documents/service 이식)

엔진(ingest/dialect/exporters)을 여기서 import 해 서비스가 엔진을 부른다(역방향 금지).
정본(canonical) HTML 은 dialect.serialize_doc 산출 — <article data-juldoc="1"> 래퍼 포함.

소유권(점진 잠금): 생성 시 principal 있으면 owner_id 부여. owner_id 있는 문서의
변경(save/delete/export)·공유 관리는 소유자만(아니면 403 NotDocumentOwner, 미인증 포함).
owner_id 없는(ownerless) 문서는 종전 무인증 동작 그대로 — 누구나 수정·삭제·공유.

juldoc 대비: id 는 UUID(str 아님) — path param 이 UUID 로 타입되므로 juldoc 의
is_valid_uuid 서비스 가드는 불필요(FastAPI 가 형식오류를 422 로 선차단).
"""
import hashlib
import uuid
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import UUID

from src.engine.doc.dialect import parse_dialect, serialize_doc
from src.engine.doc.exporters import export_docx, export_epub
from src.engine.doc.ingest import ingest
from src.engine.doc.models import BlockType, UniversalDoc
from src.features.doc.domain.models import (
    CannotDetectFormat,
    Document,
    DocumentNotFound,
    NotDocumentOwner,
    UnsupportedDocumentFormat,
)
from src.features.doc.domain.repository import DocumentRepository
from src.features.doc.domain.storage import StorageAdapter

# 정본 이미지 참조는 '/media/{key}' 상대경로다(media 서비스가 상대 URL 만 저장).
# 수출 시 이 접두어를 벗겨 storage.get(key) 로 바이트를 resolve 한다.
_MEDIA_PREFIX = "/media/"


class DocumentService:
    def __init__(self, repo: DocumentRepository, storage: StorageAdapter | None = None) -> None:
        self._repo = repo
        # storage 는 수출 시 정본 이미지 바이트 resolve 용(선택 주입). None 이면 모든
        # 이미지가 alt 폴백 — 수출 자체는 언제나 성공한다(배선 누락에 안전).
        self._storage = storage

    async def upload_document(
        self, filename: str, data: bytes, *, owner_id: UUID | None = None
    ) -> Document:
        """원본 바이트 → ingest → dialect.serialize_doc 으로 정본 HTML 생성 → 저장."""
        suffix = Path(filename or "").suffix
        if not suffix:
            raise CannotDetectFormat()

        with NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            tmp_path = Path(tmp.name)
        try:
            doc = ingest(tmp_path)
        except ValueError as e:
            raise UnsupportedDocumentFormat(str(e)) from e
        finally:
            tmp_path.unlink(missing_ok=True)

        html = serialize_doc(doc)
        fmt = str(doc.metadata.get("format", suffix.lstrip(".").lower()))
        title = Path(filename).stem or "Untitled"
        entity = self._build(
            title=title, fmt=fmt, html=html, source_hash=_sha256(data), owner_id=owner_id
        )
        return await self._repo.create(entity)

    async def create_empty(self, title: str, *, owner_id: UUID | None = None) -> Document:
        """빈 문서 생성 — 정본 HTML 은 빈 dialect 문서(<article> 래퍼)."""
        html = serialize_doc(UniversalDoc())
        entity = self._build(
            title=title or "Untitled", fmt="html", html=html, source_hash=None, owner_id=owner_id
        )
        return await self._repo.create(entity)

    async def get_document(self, doc_id: UUID) -> Document:
        doc = await self._repo.get(doc_id)
        if doc is None:
            raise DocumentNotFound()
        return doc

    async def get_document_optional(self, doc_id: UUID) -> Document | None:
        """부재/삭제 시 예외 대신 None (호출자가 은닉·멱등 판단)."""
        return await self._repo.get(doc_id)

    async def ensure_can_modify(self, doc_id: UUID, principal_id: UUID | None) -> Document:
        """변경 가능 문서를 반환하거나 거부한다.

        부재/삭제 → 404(DocumentNotFound). owner_id 있는 문서인데 principal 이 소유자가
        아니면(미인증 포함) → 403(NotDocumentOwner). ownerless 는 항상 통과.
        문서 변경·공유 관리 경로의 단일 인가 관문(shares 도 재사용).
        """
        doc = await self.get_document(doc_id)
        if doc.owner_id is not None and doc.owner_id != principal_id:
            raise NotDocumentOwner()
        return doc

    async def get_html(self, doc_id: UUID) -> str:
        return (await self.get_document(doc_id)).html

    async def save_html(
        self, doc_id: UUID, html: str, *, principal_id: UUID | None = None
    ) -> Document:
        """에디터 저장 — 받은 HTML 을 dialect 왕복으로 정규화·정화 후 정본으로 저장.

        저장형 XSS 방어선: parse_dialect 가 script/style/on* 등을 제거하고 serialize_doc 이
        <article> 래퍼 포함 정본으로 재직렬화한다. owner_id 있는 문서는 소유자만(403).
        """
        await self.ensure_can_modify(doc_id, principal_id)
        return await self.save_html_via_capability(doc_id, html)

    async def save_html_via_capability(self, doc_id: UUID, html: str) -> Document:
        """공유 EDIT 링크 저장 — 소유권 검사 없음(링크가 곧 편집 자격, 공개 접근 계약).

        소유권만 건너뛸 뿐 정화 왕복(serialize_doc∘parse_dialect)은 동일하게 통과한다 —
        공유 경로가 저장형 XSS 방어선을 우회하면 안 된다.
        """
        canonical = serialize_doc(parse_dialect(html))
        updated = await self._repo.update_html(doc_id, canonical)
        if updated is None:
            raise DocumentNotFound()
        return updated

    async def export_epub(
        self, doc_id: UUID, *, principal_id: UUID | None = None
    ) -> tuple[str, bytes]:
        """정본 HTML → parse_dialect 로 IR 복원 → 이미지 resolve → export_epub bytes.

        (제목, bytes) 반환 — 파일명·다운로드 헤더는 표현 계층 몫. 부재 404, 타인 소유 403.
        """
        doc = await self.ensure_can_modify(doc_id, principal_id)
        return doc.title, await self._render(doc, export_epub)

    async def export_epub_via_capability(self, doc_id: UUID) -> tuple[str, bytes]:
        """공유 EXPORT 링크 다운로드 — 소유권 검사 없음(링크가 곧 다운로드 자격)."""
        doc = await self.get_document(doc_id)
        return doc.title, await self._render(doc, export_epub)

    async def export_docx(
        self, doc_id: UUID, *, principal_id: UUID | None = None
    ) -> tuple[str, bytes]:
        """정본 HTML → IR 복원 → 이미지 resolve → export_docx bytes(EPUB 과 동일 경로)."""
        doc = await self.ensure_can_modify(doc_id, principal_id)
        return doc.title, await self._render(doc, export_docx)

    async def export_docx_via_capability(self, doc_id: UUID) -> tuple[str, bytes]:
        """공유 EXPORT 링크 DOCX 다운로드 — 소유권 검사 없음(링크가 곧 다운로드 자격)."""
        doc = await self.get_document(doc_id)
        return doc.title, await self._render(doc, export_docx)

    async def _render(self, doc: Document, exporter) -> bytes:
        """정본 → IR → 이미지 resolve → exporter(IR, title, images) 단일 경로.

        EPUB/DOCX 가 같은 IR 과 같은 images dict 를 공유한다(정본 단일 소스). storage
        미주입/키 부재는 그 이미지만 skip(alt 폴백) — 수출은 성공.
        """
        ir = parse_dialect(doc.html)
        images = await self._resolve_images(ir)
        return exporter(ir, doc.title, images)

    async def _resolve_images(self, doc: UniversalDoc) -> dict[str, bytes]:
        """IR 의 IMAGE 블록 src('/media/{key}') → 원본 바이트 매핑.

        storage 없거나 접두어 불일치(외부 절대 URL 등)·키 부재면 그 src 는 건너뛴다
        (exporter 가 alt 로 폴백). 같은 src 는 한 번만 조회한다(중복 제거).
        """
        if self._storage is None:
            return {}
        images: dict[str, bytes] = {}
        for page in doc.pages:
            for block in page.blocks:
                if block.type is not BlockType.IMAGE:
                    continue
                src = block.meta.get("src", "")
                if not src.startswith(_MEDIA_PREFIX) or src in images:
                    continue
                key = src[len(_MEDIA_PREFIX):]
                if not key:
                    continue
                data = await self._storage.get(key)
                if data is not None:
                    images[src] = data
        return images

    async def list_documents(
        self, page: int, page_size: int, *, viewer_id: UUID | None = None
    ) -> tuple[list[Document], int]:
        page = max(page, 1)
        page_size = max(1, min(page_size, 100))
        return await self._repo.list(page, page_size, viewer_id=viewer_id)

    async def delete_document(self, doc_id: UUID, *, principal_id: UUID | None = None) -> None:
        # 소유권 확인 후 삭제 — 부재/삭제는 ensure_can_modify 가 404.
        await self.ensure_can_modify(doc_id, principal_id)
        if not await self._repo.soft_delete(doc_id):
            raise DocumentNotFound()

    @staticmethod
    def _build(
        *, title: str, fmt: str, html: str, source_hash: str | None, owner_id: UUID | None
    ) -> Document:
        now = datetime.now(UTC)
        return Document(
            id=uuid.uuid4(),
            title=title,
            format=fmt,
            html=html,
            source_hash=source_hash,
            created_at=now,
            updated_at=now,
            owner_id=owner_id,
        )


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
