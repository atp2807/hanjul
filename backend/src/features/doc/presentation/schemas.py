"""doc API 스키마 (Pydantic). 외부 계약은 camelCase (hanjul 네이밍룰: CamelSchema).

juldoc DTO 를 이식하되 hanjul 컨벤션 적용: JSON 필드는 camelCase(createdAt·sourceHash·
displayUrl…), owner_id 는 절대 노출 안 하고 mine: bool 로만 변환(계정 id 누출 방지),
_cd/_ts 접미어 노출 금지(네이밍 린터 게이트).
"""
from datetime import datetime
from uuid import UUID

from src.presentation.schema import CamelSchema


class DocumentResponse(CamelSchema):
    """단일 문서 엔티티(정본 HTML 본문 제외 — 그것은 /html 엔드포인트).

    mine: 현재 요청 주체가 이 문서의 소유자인지. ownerless 문서는 항상 False.
    """

    id: UUID
    title: str
    format: str
    source_hash: str | None
    created_at: datetime
    updated_at: datetime
    mine: bool = False


class DocumentListResponse(CamelSchema):
    items: list[DocumentResponse]
    total: int
    page: int
    page_size: int


class UploadResponse(CamelSchema):
    id: UUID
    title: str
    format: str


class CreateDocumentRequest(CamelSchema):
    title: str = "Untitled"


class UpdateHtmlRequest(CamelSchema):
    html: str


class CreateShareRequest(CamelSchema):
    # capability: "view" | "edit" | "export".
    capability: str


class ShareResponse(CamelSchema):
    """발급/목록 항목. url 은 공개 페이지 경로("/doc/s/" + token, 실제 웹 라우트)."""

    id: UUID
    token: str
    url: str
    capability: str
    created_at: datetime
    revoked: bool


class ShareListResponse(CamelSchema):
    items: list[ShareResponse]
    total: int
    page: int
    page_size: int


class ShareMetaResponse(CamelSchema):
    """공개 페이지 부트스트랩 — 문서 제목 + 권한(VIEW/EDIT 분기용)."""

    title: str
    capability: str


class UpdateShareHtmlRequest(CamelSchema):
    html: str


class MediaResponse(CamelSchema):
    """미디어 업로드 응답. 모든 url 은 상대경로 '/media/{key}' — 절대 URL 저장/노출 금지.

    서빙 시점(GET /api/media/{key})에 R2 공개 URL 로 리다이렉트하거나 로컬 프록시한다.
      url         : 원본(업로드 바이트 그대로).
      display_url : 최대 변 1600px webp — 프론트가 문서 본문 img src 로 사용.
      thumb_url   : 최대 변 320px webp — 목록/미리보기용.
    """

    url: str
    display_url: str
    thumb_url: str
    bytes: int
    content_type: str
    width: int
    height: int
