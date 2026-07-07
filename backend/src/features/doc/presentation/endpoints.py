"""doc API 엔드포인트 — juldoc 경로 그대로(api.py 가 /api prefix 부여).

최종 경로: POST /api/documents/upload, /api/documents, /api/documents/{id}(+/html,/export),
공유 6종(/api/documents/{id}/shares, /api/shares/…), 미디어 POST /api/media·GET /api/media/{key}.
(정본 HTML 안 이미지 src 는 상대 '/media/{key}' 불변 — 프론트가 렌더 시 ${apiBase}/api/media/{key} 로 매핑.)

인증: 필수 아닌 곳은 optional(get_current_account_optional) — 비로그인 허용. 로그인 상태면
소유권 부여/검사(점진 잠금). 업로드 크기 상한은 books HWP/PDF import 와 동일하게 엔드포인트
에서 len 검사 → 413(HTTPException).
"""
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from src.features.auth.domain.models import AccountPrincipal
from src.features.auth.presentation.dependencies import get_current_account_optional
from src.features.doc.application.document_service import DocumentService
from src.features.doc.application.media_service import MediaService
from src.features.doc.application.share_service import ShareService
from src.features.doc.application.uploads import content_type_for_key
from src.features.doc.domain.models import Document, MediaNotFound, ShareLink
from src.features.doc.presentation.dependencies import (
    get_document_service,
    get_media_service,
    get_share_service,
)
from src.features.doc.presentation.schemas import (
    CreateDocumentRequest,
    CreateShareRequest,
    DocumentListResponse,
    DocumentResponse,
    MediaResponse,
    ShareListResponse,
    ShareMetaResponse,
    ShareResponse,
    UpdateHtmlRequest,
    UpdateShareHtmlRequest,
    UploadResponse,
)

router = APIRouter(tags=["doc"])

# 업로드 크기 상한(books HWP/PDF import 관례). 문서 원본 20MB, 미디어 본문 12MB(이미지 10MB + 여유).
_DOC_UPLOAD_MAX_BYTES = 20 * 1024 * 1024
_MEDIA_MAX_BYTES = 12 * 1024 * 1024

_DOCX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


def _principal_id(principal: AccountPrincipal | None) -> UUID | None:
    return principal.id if principal is not None else None


def _to_response(doc: Document, principal_id: UUID | None) -> DocumentResponse:
    """도메인 엔티티 → DTO. owner_id 는 mine: bool 로만 변환(계정 id 누출 방지)."""
    return DocumentResponse(
        id=doc.id,
        title=doc.title,
        format=doc.format,
        source_hash=doc.source_hash,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        mine=doc.owner_id is not None and doc.owner_id == principal_id,
    )


def _to_share_response(share: ShareLink) -> ShareResponse:
    return ShareResponse(
        id=share.id,
        token=share.token,
        url=f"/doc/s/{share.token}",
        capability=str(share.capability),
        created_at=share.created_at,
        revoked=share.revoked,
    )


def _download_response(title: str, data: bytes, ext: str, media_type: str) -> Response:
    """bytes → 다운로드 Response. 한글 제목용 RFC 5987 filename*(UTF-8) + ASCII 폴백."""
    stem = (title or "").strip() or "document"
    ascii_stem = "".join(c for c in stem if c.isascii() and c not in '"\\/') or "document"
    quoted = quote(f"{stem}.{ext}")
    disposition = f'attachment; filename="{ascii_stem}.{ext}"; filename*=UTF-8\'\'{quoted}'
    return Response(
        content=data, media_type=media_type, headers={"Content-Disposition": disposition}
    )


def epub_download_response(title: str, data: bytes) -> Response:
    return _download_response(title, data, "epub", "application/epub+zip")


def docx_download_response(title: str, data: bytes) -> Response:
    return _download_response(title, data, "docx", _DOCX_MEDIA_TYPE)


# ── 문서 ─────────────────────────────────────────────────────────


@router.post("/documents/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    service: DocumentService = Depends(get_document_service),
    principal: AccountPrincipal | None = Depends(get_current_account_optional),
) -> UploadResponse:
    # 로그인이면 owner_id 부여(잠김), 비로그인이면 ownerless(종전 동작).
    data = await file.read()
    if len(data) > _DOC_UPLOAD_MAX_BYTES:
        raise HTTPException(413, "원고 파일은 20MB 이하여야 해요.")
    doc = await service.upload_document(
        file.filename or "", data, owner_id=_principal_id(principal)
    )
    return UploadResponse(id=doc.id, title=doc.title, format=doc.format)


@router.post("/documents", response_model=UploadResponse)
async def create_document(
    body: CreateDocumentRequest,
    service: DocumentService = Depends(get_document_service),
    principal: AccountPrincipal | None = Depends(get_current_account_optional),
) -> UploadResponse:
    doc = await service.create_empty(body.title, owner_id=_principal_id(principal))
    return UploadResponse(id=doc.id, title=doc.title, format=doc.format)


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: DocumentService = Depends(get_document_service),
    principal: AccountPrincipal | None = Depends(get_current_account_optional),
) -> DocumentListResponse:
    # 로그인: 내 문서 + ownerless. 비로그인: ownerless 만.
    pid = _principal_id(principal)
    items, total = await service.list_documents(page, page_size, viewer_id=pid)
    return DocumentListResponse(
        items=[_to_response(d, pid) for d in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: UUID,
    service: DocumentService = Depends(get_document_service),
    principal: AccountPrincipal | None = Depends(get_current_account_optional),
) -> DocumentResponse:
    doc = await service.get_document(doc_id)
    return _to_response(doc, _principal_id(principal))


@router.get("/documents/{doc_id}/html", response_class=HTMLResponse)
async def get_document_html(
    doc_id: UUID,
    service: DocumentService = Depends(get_document_service),
) -> HTMLResponse:
    return HTMLResponse(content=await service.get_html(doc_id))


@router.put("/documents/{doc_id}/html", response_model=DocumentResponse)
async def update_document_html(
    doc_id: UUID,
    body: UpdateHtmlRequest,
    service: DocumentService = Depends(get_document_service),
    principal: AccountPrincipal | None = Depends(get_current_account_optional),
) -> DocumentResponse:
    pid = _principal_id(principal)
    doc = await service.save_html(doc_id, body.html, principal_id=pid)
    return _to_response(doc, pid)


@router.get("/documents/{doc_id}/export/epub")
async def export_document_epub(
    doc_id: UUID,
    service: DocumentService = Depends(get_document_service),
    principal: AccountPrincipal | None = Depends(get_current_account_optional),
) -> Response:
    title, data = await service.export_epub(doc_id, principal_id=_principal_id(principal))
    return epub_download_response(title, data)


@router.get("/documents/{doc_id}/export/docx")
async def export_document_docx(
    doc_id: UUID,
    service: DocumentService = Depends(get_document_service),
    principal: AccountPrincipal | None = Depends(get_current_account_optional),
) -> Response:
    title, data = await service.export_docx(doc_id, principal_id=_principal_id(principal))
    return docx_download_response(title, data)


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: UUID,
    service: DocumentService = Depends(get_document_service),
    principal: AccountPrincipal | None = Depends(get_current_account_optional),
) -> dict:
    await service.delete_document(doc_id, principal_id=_principal_id(principal))
    return {"id": str(doc_id), "deleted": True}


# ── 공유 ─────────────────────────────────────────────────────────


@router.post("/documents/{doc_id}/shares", response_model=ShareResponse, status_code=201)
async def create_share(
    doc_id: UUID,
    body: CreateShareRequest,
    service: ShareService = Depends(get_share_service),
    principal: AccountPrincipal | None = Depends(get_current_account_optional),
) -> ShareResponse:
    share = await service.create_share(
        doc_id, body.capability, principal_id=_principal_id(principal)
    )
    return _to_share_response(share)


@router.get("/documents/{doc_id}/shares", response_model=ShareListResponse)
async def list_shares(
    doc_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    service: ShareService = Depends(get_share_service),
    principal: AccountPrincipal | None = Depends(get_current_account_optional),
) -> ShareListResponse:
    # 토큰 목록 = 접근 자격 전량 노출 — owned 문서는 소유자만(403). ownerless 는 누구나.
    items, total = await service.list_shares(
        doc_id, page, page_size, principal_id=_principal_id(principal)
    )
    return ShareListResponse(
        items=[_to_share_response(s) for s in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.delete("/shares/{share_id}", status_code=204)
async def revoke_share(
    share_id: UUID,
    service: ShareService = Depends(get_share_service),
    principal: AccountPrincipal | None = Depends(get_current_account_optional),
) -> Response:
    # 멱등 — 이미 회수됐거나 없어도 204. owner_id 있는 문서는 소유자만(403).
    await service.revoke_share(share_id, principal_id=_principal_id(principal))
    return Response(status_code=204)


@router.get("/shares/{token}", response_model=ShareMetaResponse)
async def get_share_meta(
    token: str,
    service: ShareService = Depends(get_share_service),
) -> ShareMetaResponse:
    title, capability = await service.get_share_meta(token)
    return ShareMetaResponse(title=title, capability=str(capability))


@router.get("/shares/{token}/html", response_class=HTMLResponse)
async def get_share_html(
    token: str,
    service: ShareService = Depends(get_share_service),
) -> HTMLResponse:
    return HTMLResponse(content=await service.get_share_html(token))


@router.get("/shares/{token}/export/epub")
async def export_share_epub(
    token: str,
    service: ShareService = Depends(get_share_service),
) -> Response:
    # EXPORT 링크만. 아니면 403(권한부족), 회수/부재는 404.
    title, data = await service.export_epub(token)
    return epub_download_response(title, data)


@router.get("/shares/{token}/export/docx")
async def export_share_docx(
    token: str,
    service: ShareService = Depends(get_share_service),
) -> Response:
    title, data = await service.export_docx(token)
    return docx_download_response(title, data)


@router.put("/shares/{token}/html", status_code=204)
async def save_share_html(
    token: str,
    body: UpdateShareHtmlRequest,
    service: ShareService = Depends(get_share_service),
) -> Response:
    # EDIT 아닌 링크면 403. 저장은 문서 정화 왕복(저장형 XSS 방어선)을 통과한다.
    await service.save_share_html(token, body.html)
    return Response(status_code=204)


# ── 미디어 ───────────────────────────────────────────────────────


@router.post("/media", response_model=MediaResponse, status_code=201)
async def upload_media(
    file: UploadFile = File(...),
    service: MediaService = Depends(get_media_service),
    _principal: AccountPrincipal | None = Depends(get_current_account_optional),
) -> MediaResponse:
    # 크기 상한(413)은 검증 전 버퍼링 위험 차단(books import 관례). validate_image 가
    # 이미지 10MB 상한(422)을 재확인. 매직바이트 위조/치수 위반도 422(도메인 MediaError).
    data = await file.read()
    if len(data) > _MEDIA_MAX_BYTES:
        raise HTTPException(413, "이미지 파일은 12MB 이하여야 해요.")
    result = await service.upload(data, file.filename or "")
    return MediaResponse(
        url=result.url,
        display_url=result.display_url,
        thumb_url=result.thumb_url,
        bytes=result.bytes,
        content_type=result.content_type,
        width=result.width,
        height=result.height,
    )


@router.get("/media/{key}")
async def serve_media(
    key: str, service: MediaService = Depends(get_media_service)
) -> Response:
    """R2 면 공개 URL 로 302 리다이렉트, 로컬이면 바이트 프록시. 없으면 404.

    분기 기준: url_for 가 절대 URL('://')이면 R2, 상대면 로컬 프록시.
    """
    storage = service.storage
    target = storage.url_for(key)
    if "://" in target:
        if not await storage.exists(key):
            raise MediaNotFound()
        return RedirectResponse(target, status_code=302)
    data = await storage.get(key)
    if data is None:
        raise MediaNotFound()
    return Response(content=data, media_type=content_type_for_key(key))
