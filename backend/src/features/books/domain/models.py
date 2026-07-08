"""books 도메인 — persistence-agnostic 뷰 모델 + 에러.

리포지토리는 ORM 객체가 아니라 이 dataclass 들을 반환한다 → 서비스/표현 레이어가
SQLAlchemy 에 의존하지 않고, 인메모리 Fake 로 테스트 가능.
"""
from dataclasses import dataclass, field
from uuid import UUID

from src.shared.errors import ForbiddenError, NotFoundError


@dataclass
class BlockView:
    id: UUID
    order_no: int
    block_type: str
    html: str


@dataclass
class ChapterView:
    id: UUID
    title: str | None
    order_no: int
    blocks: list[BlockView] = field(default_factory=list)


@dataclass
class BookView:
    id: UUID
    title: str
    kind: str
    language: str
    status: str
    price_amt: int | None = None
    preview_limit: int = 3
    # 콘텐츠 연령등급 (플랫폼 자율등급, 8기준 중 최댓값). ALL|AGE12|AGE15|AGE18.
    content_rating: str = "ALL"
    # 8기준별 세부 등급 {theme, violence, …}. None = 아직 미분류.
    content_rating_detail: dict | None = None
    chapters: list[ChapterView] = field(default_factory=list)


def to_preview(content: BookView, limit: int) -> BookView:
    """앞 limit개 블록만 남긴 미리보기 뷰 (장 경계 가로질러 누적)."""
    remaining = limit
    chapters: list[ChapterView] = []
    for ch in content.chapters:
        if remaining <= 0:
            break
        blocks = ch.blocks[:remaining]
        remaining -= len(blocks)
        chapters.append(ChapterView(id=ch.id, title=ch.title, order_no=ch.order_no, blocks=blocks))
    return BookView(
        id=content.id,
        title=content.title,
        kind=content.kind,
        language=content.language,
        status=content.status,
        price_amt=content.price_amt,
        chapters=chapters,
    )


def suggest_blurb(content: BookView, limit: int = 150) -> str:
    """본문 앞부분에서 소개문을 추천 (HTML 제거·공백 정규화). LLM 고도화는 키 주입 시."""
    import re

    parts = [
        re.sub(r"<[^>]+>", "", b.html)
        for ch in content.chapters
        for b in ch.blocks
        if b.block_type != "HR"
    ]
    text = re.sub(r"\s+", " ", " ".join(parts)).strip()
    return f"{text[:limit]}…" if len(text) > limit else text


def extract_text(content: BookView) -> str:
    """정본 전체를 평문으로 추출 (HTML 태그 제거·공백 정규화). 길이제한 없음.

    등급 자동분류 입력용. suggest_blurb과 같은 방식이나 앞부분만이 아닌 전체를 반환한다 —
    AI 프롬프트로 보낼 때의 비용 통제(최대 6000자 컷)는 상위 레이어(서비스)에서 한다.
    """
    import re

    parts = [
        re.sub(r"<[^>]+>", "", b.html)
        for ch in content.chapters
        for b in ch.blocks
        if b.block_type != "HR"
    ]
    return re.sub(r"\s+", " ", " ".join(parts)).strip()


@dataclass
class ImportResult:
    chapter_id: UUID
    block_count: int


class BookNotFound(NotFoundError):
    """요청한 책이 존재하지 않음 → 404."""

    def __init__(self, book_id: UUID | None = None):
        self.book_id = book_id
        super().__init__("책을 찾을 수 없어요.")


class NotOwner(ForbiddenError):
    """책의 작가가 아닌 사용자의 변경 시도 → 403."""

    def __init__(self, book_id: UUID | None = None):
        self.book_id = book_id
        super().__init__("이 책의 작가만 변경할 수 있어요.")


class NotPurchased(ForbiddenError):
    """EPUB 등 완본 다운로드 — 무료도 구매도 아니면 거부(403). 리더 콘텐츠 엔드포인트의
    is_free/owned 로직과 동일 기준 — 이 경로는 미리보기 개념이 없어 부분 허용 대신 전면 차단."""

    def __init__(self, book_id: UUID | None = None):
        self.book_id = book_id
        super().__init__("구매 후 다운로드할 수 있어요.")
