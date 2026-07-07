"""doc 도메인 — persistence-agnostic 값객체 + 에러.

리포지토리는 ORM 이 아니라 이 dataclass 를 반환한다 → 서비스/표현 레이어가 SQLAlchemy 에
의존하지 않고 인메모리 Fake 로 테스트 가능(books 컨벤션과 동일).

juldoc 대비: 도메인 에러는 juldoc 의 error_code(DOC_001·SHARE_001…) 문자열 대신
hanjul shared/errors 서브클래스로 표현한다 — HTTP **상태 의미는 그대로 보존**한다
(404 은닉·403 인가·422 검증). error_code 응답 필드는 hanjul 계약에 없다(중앙 핸들러가
{"detail": …} 로 직렬화). id 는 hanjul 전역 규약대로 UUID(books.BookView.id 와 동일).
"""
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from src.shared.errors import DomainError, ForbiddenError, NotFoundError, ValidationError


class Capability(StrEnum):
    """공유 링크 권한. 값은 DB(capability_cd)·API(capability)에 그대로 나가는 친화 소문자.

    서열: VIEW < EDIT / EXPORT. EDIT⊥EXPORT(직교) —
      VIEW   = 열람만
      EDIT   = 편집 + 열람 (export 불가)
      EXPORT = 열람 + 다운로드 (편집 불가, VIEW ⊂ EXPORT)
    """
    VIEW = "view"
    EDIT = "edit"
    EXPORT = "export"


@dataclass
class Document:
    """정본 HTML 문서 엔티티. 표현 계층으로 매핑되기 전 도메인 값.

    owner_id: None = 공용(ownerless, 종전 무인증 동작), 값 존재 = 잠김.
    표현 계층으로는 owner_id 를 직접 노출하지 않고 mine: bool 로 변환한다(계정 id 누출 방지).
    """
    id: UUID
    title: str
    format: str
    html: str
    source_hash: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
    owner_id: UUID | None = None


@dataclass
class ShareLink:
    id: UUID
    document_id: UUID
    token: str
    capability: Capability
    created_at: datetime
    revoked_at: datetime | None = None

    @property
    def revoked(self) -> bool:
        return self.revoked_at is not None


# ── 문서/공유 도메인 에러 (HTTP 상태 의미는 juldoc 그대로) ──────────────────


class DocumentNotFound(NotFoundError):
    """부재/삭제 문서 → 404 (juldoc DOC_001)."""
    default_detail = "문서를 찾을 수 없어요."


class NotDocumentOwner(ForbiddenError):
    """owner_id 있는 문서를 소유자 아닌 주체(미인증 포함)가 변경/공유관리 시도 → 403 (juldoc AUTH_003)."""
    default_detail = "이 문서의 소유자만 변경할 수 있어요."


class CannotDetectFormat(ValidationError):
    """업로드 파일에 확장자가 없어 포맷 판정 불가 → 422 (juldoc DOC_002)."""
    default_detail = "파일 형식을 판별할 수 없어요."


class UnsupportedDocumentFormat(DomainError):
    """지원하지 않는 포맷/파싱 실패 → 400 (juldoc DOC_002)."""
    status_code = 400
    default_detail = "지원하지 않는 문서 형식이에요."


class ShareNotFound(NotFoundError):
    """회수/부재/삭제된 공유 링크 → 404. 회수와 부재를 구분하지 않고 동일 은닉 (juldoc SHARE_001)."""
    default_detail = "공유 링크를 찾을 수 없어요."


class ShareCapabilityDenied(ForbiddenError):
    """링크 권한 부족(VIEW 로 편집/다운로드 시도 등) → 403 (juldoc SHARE_002)."""
    default_detail = "이 공유 링크로는 할 수 없는 작업이에요."


class UnknownCapability(ValidationError):
    """알 수 없는 capability 값 → 422 (juldoc SHARE_003)."""
    default_detail = "알 수 없는 공유 권한이에요."


# ── 미디어 도메인 에러 (전부 422, 서빙 부재만 404) ─────────────────────────
# juldoc MEDIA_001~005 를 서브클래스로 세분(모두 422). 상태 500 이 새지 않게 검증 계층에서
# 흡수하는 것이 핵심(특히 decompression bomb → CorruptImage/치수초과 아닌 422).


class MediaError(ValidationError):
    """미디어 검증 실패 뿌리 → 422."""
    default_detail = "이미지를 처리할 수 없어요."


class UnsupportedImageFormat(MediaError):
    """허용 안 된 매직바이트(JPEG/PNG/GIF/WEBP 외)·디코드 실패 → 422 (juldoc MEDIA_001)."""
    default_detail = "허용되지 않는 이미지 형식이에요. (JPEG, PNG, GIF, WEBP만 가능)"


class ImageTooLarge(MediaError):
    """이미지 바이트 상한(10MB) 초과 → 422 (juldoc MEDIA_002)."""
    default_detail = "이미지 크기가 상한을 초과했어요."


class ImageDimensionTooLarge(MediaError):
    """최대 변 상한(4096px) 초과 → 422. decompression bomb 방어선 (juldoc MEDIA_003)."""
    default_detail = "이미지 최대 변이 상한을 초과했어요."


class ImageDimensionTooSmall(MediaError):
    """최소 변 하한(32px) 미만 → 422. 추적픽셀/파편 차단 (juldoc MEDIA_004)."""
    default_detail = "이미지가 너무 작아요."


class CorruptImage(MediaError):
    """손상/빈 껍데기 이미지 → 422 (juldoc MEDIA_005)."""
    default_detail = "이미지 파일이 손상됐거나 비어 있어요."


class MediaNotFound(NotFoundError):
    """서빙 요청한 미디어 키가 저장소에 없음 → 404 (juldoc MEDIA_404)."""
    default_detail = "미디어를 찾을 수 없어요."
