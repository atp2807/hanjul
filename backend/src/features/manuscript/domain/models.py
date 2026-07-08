"""manuscript 도메인 — 데스크탑 원고의 일방향 백업(append-only 리비전 로그).

한줄 IDE P1 슬라이스7. 데스크탑(desktop/store.py SQLite)이 정본이고 서버는 백업
수신처(단방향 push)다 — 양방향 동기화(P2)의 토대만 여기서 놓는다. `sync_key`(UUID,
데스크탑이 생성)가 데스크탑 `book.sync_key` ↔ 서버 `ms.manuscript_book`을 잇는 안정적
식별자다 — 로컬 자동증분 id와 무관해 재설치·재발행에도 같은 책으로 인식된다.

챕터 리비전은 append-only — 매 push마다 챕터별 **최신** 리비전과 `content_hash`가
같으면 skip(dedup, 잦은 자동저장이 매번 새 리비전을 쌓지 않게), 다르면 새 리비전을
append한다. 리비전은 절대 UPDATE하지 않는다 — 유일한 삭제는 챕터당 상한(`prune`)이다.

`content_hash`는 클라이언트가 계산한 sha256(html)을 그대로 신뢰한다 — 서버가 재계산해
검증하지 않는다(이 슬라이스는 **백업**이지 무결성 프로토콜이 아니다: 위변조 방지가
아니라 "타이핑 중 잦은 자동저장이 매번 새 리비전을 쌓지 않게"가 유일한 목적).
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.shared.errors import ForbiddenError, NotFoundError

# 챕터당 보관 리비전 상한 — 초과 시 오래된 것부터 prune (payouts/store.py 스냅샷과 동일 원칙).
MAX_REVISIONS_PER_CHAPTER = 50


@dataclass
class ManuscriptBookView:
    id: UUID
    account_id: UUID
    sync_key: UUID
    title: str
    created_at: datetime
    updated_at: datetime


@dataclass
class ChapterPush:
    """PUT 요청 본문의 챕터 1개 — 클라이언트가 이미 계산한 content_hash 포함."""
    chapter_key: str
    title: str
    html: str
    content_hash: str


@dataclass
class PushResult:
    saved_count: int
    skipped_count: int


@dataclass
class ChapterState:
    """GET 응답의 챕터 1개 — 챕터별 최신 리비전(복원/동기화 토대, P2)."""
    chapter_key: str
    title: str
    html: str
    content_hash: str
    updated_at: datetime


class ManuscriptNotFound(NotFoundError):
    default_detail = "백업된 원고를 찾을 수 없어요."


class NotManuscriptOwner(ForbiddenError):
    """sync_key 가 가리키는 책이 이미 다른 계정 소유 — 토큰 도용/충돌 방지."""
    default_detail = "이 원고에 접근할 권한이 없어요."


class ManuscriptRepository(Protocol):
    async def get_book_by_sync_key(self, sync_key: UUID) -> ManuscriptBookView | None: ...

    async def create_book(self, account_id: UUID, sync_key: UUID, title: str) -> ManuscriptBookView: ...

    async def touch_book(self, book_id: UUID, title: str) -> None:
        """push마다 제목 갱신 + updated_ts 갱신(데스크탑이 정본이므로 서버 쪽 표시용 제목도 최신화)."""
        ...

    async def push_chapter(
        self, book_id: UUID, chapter_key: str, chapter_title: str, html: str, content_hash: str
    ) -> bool:
        """챕터 최신 리비전과 content_hash 비교 후 다르면 append + prune.

        반환: 저장했으면 True(saved), dedup으로 건너뛰었으면 False(skipped).
        """
        ...

    async def latest_state(self, book_id: UUID) -> list[ChapterState]:
        """챕터별 최신 리비전만 모은 현재 상태(복원/P2 동기화 토대)."""
        ...
