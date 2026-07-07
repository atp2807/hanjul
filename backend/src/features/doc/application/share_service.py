"""공유 유스케이스 계층 — ShareRepository Protocol + DocumentService 에 의존. (juldoc shares/service 이식)

정화 왕복 재사용: PUT html 은 DocumentService.save_html_via_capability 를 호출한다 —
serialize_doc(parse_dialect(html)) 왕복이 저장형 XSS 방어선이며, 공유 경로가 그 방어선을
우회하는 별도 저장 경로를 만들면 안 된다.

회수/부재 은닉: get_by_token 이 None 이거나 revoked 이면 동일하게 ShareNotFound(404) —
"회수됨" 과 "존재 안 함" 을 구분하는 정보를 노출하지 않는다.
"""
import secrets
import uuid
from datetime import UTC, datetime
from uuid import UUID

from src.features.doc.application.document_service import DocumentService
from src.features.doc.domain.models import (
    Capability,
    Document,
    DocumentNotFound,
    NotDocumentOwner,
    ShareCapabilityDenied,
    ShareLink,
    ShareNotFound,
    UnknownCapability,
)
from src.features.doc.domain.repository import ShareRepository

_TOKEN_BYTES = 24  # secrets.token_urlsafe(24) → 32자 URL-safe 토큰.


class ShareService:
    def __init__(self, repo: ShareRepository, documents: DocumentService) -> None:
        self._repo = repo
        self._documents = documents

    # ── 발급/회수 ──────────────────────────────────────────────────
    # 소유권: owner_id 있는 문서의 링크 발급·회수·목록은 소유자만(아니면 403, 미인증 포함).
    # ownerless 문서는 종전대로 누구나. 공개 접근(토큰)은 소유권 무관.

    async def create_share(
        self, doc_id: UUID, capability: str, *, principal_id: UUID | None = None
    ) -> ShareLink:
        """공유 링크 발급. VIEW/EDIT/EXPORT 모두 발급 가능(알 수 없는 값만 422)."""
        cap = self._parse_capability(capability)
        # 부재/삭제 문서는 404, owner_id 있으면 소유자만 403.
        await self._documents.ensure_can_modify(doc_id, principal_id)
        share = ShareLink(
            id=uuid.uuid4(),
            document_id=doc_id,
            token=secrets.token_urlsafe(_TOKEN_BYTES),
            capability=cap,
            created_at=datetime.now(UTC),
        )
        return await self._repo.create(share)

    async def list_shares(
        self, doc_id: UUID, page: int, page_size: int, *, principal_id: UUID | None = None
    ) -> tuple[list[ShareLink], int]:
        """발급 목록 조회 — 발급/회수와 동일한 소유권 관문을 통과한다.

        토큰 목록은 문서 접근 자격(살아있는 토큰) 전량 노출이므로 owned 문서는 소유자만
        (아니면 403, 미인증 포함). ownerless 는 종전대로 누구나. 부재 문서는 404.
        """
        page = max(page, 1)
        page_size = max(1, min(page_size, 100))
        await self._documents.ensure_can_modify(doc_id, principal_id)
        return await self._repo.list_by_document(doc_id, page, page_size)

    async def revoke_share(self, share_id: UUID, *, principal_id: UUID | None = None) -> None:
        """회수. 멱등 — 이미 회수됐거나 없어도 조용히 성공(204).

        소유권: 대상 문서가 owner_id 있으면 소유자만 회수(아니면 403). 문서가 그새 삭제됐으면
        소유권 판단 불가 → 무해한 멱등 no-op 로 둔다.
        """
        share = await self._repo.get_by_id(share_id)
        if share is None:
            return  # 부재 → 멱등 no-op
        doc = await self._documents.get_document_optional(share.document_id)
        if doc is not None and doc.owner_id is not None and doc.owner_id != principal_id:
            raise NotDocumentOwner()
        await self._repo.revoke(share_id)

    # ── 공개 접근(토큰) ────────────────────────────────────────────

    async def get_share_meta(self, token: str) -> tuple[str, Capability]:
        """공개 페이지 부트스트랩 — (문서 제목, 권한)."""
        share = await self._resolve_active_share(token)
        doc = await self._active_document(share.document_id)
        return doc.title, share.capability

    async def get_share_html(self, token: str) -> str:
        """정본 HTML — VIEW/EDIT 공통."""
        share = await self._resolve_active_share(token)
        doc = await self._active_document(share.document_id)
        return doc.html

    async def save_share_html(self, token: str, html: str) -> None:
        """EDIT 권한 링크만 저장. DocumentService 재사용(정화 왕복 통과)."""
        share = await self._resolve_active_share(token)
        if share.capability is not Capability.EDIT:
            raise ShareCapabilityDenied("이 공유 링크는 읽기 전용이에요.")
        try:
            # 링크가 곧 편집 자격 — 소유권은 건너뛰되(via_capability) 정화 왕복은 동일 통과.
            await self._documents.save_html_via_capability(share.document_id, html)
        except DocumentNotFound as e:
            # 문서가 그새 사라짐 → 부재/회수와 동일하게 은닉.
            raise ShareNotFound() from e

    async def export_epub(self, token: str) -> tuple[str, bytes]:
        """EXPORT 권한 링크만 다운로드. (제목, EPUB bytes) 반환."""
        return await self._export(token, self._documents.export_epub_via_capability)

    async def export_docx(self, token: str) -> tuple[str, bytes]:
        """EXPORT 권한 링크만 DOCX 다운로드. (제목, DOCX bytes) 반환."""
        return await self._export(token, self._documents.export_docx_via_capability)

    async def _export(self, token: str, exporter) -> tuple[str, bytes]:
        """EXPORT 게이트 + 은닉을 공유하는 다운로드 헬퍼(EPUB/DOCX 공통).

        capability 가 EXPORT 가 아니면 403(ShareCapabilityDenied) — EDIT⊥EXPORT 라 EDIT
        링크로도 불가. 회수/부재/삭제 문서는 ShareNotFound(404) 로 은닉.
        """
        share = await self._resolve_active_share(token)
        if share.capability is not Capability.EXPORT:
            raise ShareCapabilityDenied("이 공유 링크로는 다운로드할 수 없어요.")
        try:
            # 링크가 곧 다운로드 자격 — 소유권 검사 없이 export(via_capability).
            return await exporter(share.document_id)
        except DocumentNotFound as e:
            raise ShareNotFound() from e

    # ── 내부 헬퍼 ──────────────────────────────────────────────────

    async def _resolve_active_share(self, token: str) -> ShareLink:
        """실조회 후 회수/부재를 동일하게 404(ShareNotFound) 로 은닉."""
        share = await self._repo.get_by_token(token)
        if share is None or share.revoked_at is not None:
            raise ShareNotFound()
        return share

    async def _active_document(self, doc_id: UUID) -> Document:
        """대상 문서 조회 — soft-delete/부재면 ShareNotFound 로 은닉(DocumentNotFound 누출 금지)."""
        try:
            return await self._documents.get_document(doc_id)
        except DocumentNotFound as e:
            raise ShareNotFound() from e

    @staticmethod
    def _parse_capability(value: str) -> Capability:
        # 서열: VIEW < EDIT(편집+열람) / EXPORT(열람+다운로드). EDIT⊥EXPORT(직교).
        # 알 수 없는 값만 422(UnknownCapability).
        try:
            return Capability(value)
        except ValueError as e:
            raise UnknownCapability(f"알 수 없는 공유 권한이에요: {value!r}") from e
