"""한줄 IDE P1 슬라이스7 — 백업 push. 데스크탑 원고(SQLite)를 hanjul 백엔드에 일방향으로
밀어넣는다(리비전 로그 append-only, 양방향 동기화는 P2). publisher.py 의 urllib 기반
`_request()`(Bearer 토큰 헤더 포함, 4xx/5xx는 PublishHttpError)를 그대로 재사용한다 — 새
HTTP 클라이언트를 만들지 않는다.

실측 근거(2026-07-08, file:line 인용) — 서버 계약:
- `PUT /api/manuscripts/{syncKey}` body `{title, chapters:[{chapterKey,title,html,contentHash}]}`
  → 200 `{savedCount, skippedCount}`
  (backend/src/features/manuscript/presentation/endpoints.py:26-45,
  schemas.py:8-19 `ManuscriptPushRequest`/`ManuscriptPushResponse`). 인증 필수(Bearer) —
  없으면 401(get_current_account, auth/presentation/dependencies.py:43-50).
  책이 없으면(sync_key 최초 push) 요청자 소유로 자동 생성, 있는데 다른 계정 소유면 403
  (manuscript/application/manuscript_service.py:24-35 `NotManuscriptOwner`).
- 챕터별 dedup — 서버가 최신 리비전의 content_hash 와 비교해 같으면 skip, 다르면 append
  (manuscript/infrastructure/manuscript_repo.py:47-64 `push_chapter`). 이 모듈은 매번
  전체 챕터를 그대로 보내면 된다 — 스킵 판단은 전적으로 서버 책임(로컬에서 미리 걸러내지
  않는다, 서버 최신 해시를 로컬이 알 방법이 없어서다).
- `GET /api/manuscripts/{syncKey}`(최신 상태 조회, P2 복원/동기화 토대)는 서버에 이미
  구현돼 있으나 이 슬라이스(push 전용)는 호출하지 않는다.

content_hash = sha256(html) — 클라이언트가 계산해 그대로 전달한다. 서버는 재계산·검증하지
않는다(manuscript/domain/models.py 모듈 docstring — "이 슬라이스는 백업이지 무결성
프로토콜이 아니다"). 이 모듈 자체는 실패를 조용히 삼키지 않고 PublishHttpError 를 그대로
올린다 — "백업 실패가 앱 기능에 영향 0"이어야 하는 책임은 호출자(app.py)에 있다(수동
[백업] 버튼은 실패를 사용자에게 보여줘야 하고, 자동 백업 스레드는 조용히 삼켜야 해서
호출자마다 다르게 처리해야 하기 때문 — 이 모듈에서 미리 삼키면 그 구분이 불가능해진다).
"""
from __future__ import annotations

import hashlib

from publisher import _request  # noqa: E402  (재사용 — urllib + Bearer + JSON 처리)


def _sha256(html: str) -> str:
    return hashlib.sha256(html.encode("utf-8")).hexdigest()


def backup_now(store, settings: dict | None) -> dict:
    """book.sync_key 로 서버에 전체 챕터(title+html)를 push.

    반환: ``{"savedCount": int, "skippedCount": int}``. 로컬 챕터가 하나도 없으면(이론상
    발생 안 함 — Store가 항상 챕터 1개를 시드) chapters=[] 로 그냥 보낸다(서버가 0/0으로
    답함, 별도 분기 불필요).

    실패(연결 실패·4xx/5xx)는 publisher.PublishHttpError 를 그대로 전파한다 — 삼키지 않음.
    """
    book = store.get_book()
    sync_key = store.get_sync_key()
    chapters = []
    for summary in store.list_chapters():
        full = store.load_chapter(summary["id"])
        chapters.append(
            {
                "chapterKey": str(full["id"]),
                "title": full["title"],
                "html": full["html"],
                "contentHash": _sha256(full["html"]),
            }
        )

    _, body = _request(
        settings,
        "PUT",
        f"/manuscripts/{sync_key}",
        {"title": book["title"], "chapters": chapters},
    )
    return {"savedCount": body["savedCount"], "skippedCount": body["skippedCount"]}
