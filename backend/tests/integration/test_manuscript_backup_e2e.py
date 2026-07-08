"""manuscript(데스크탑 원고 백업) E2E — push(생성/dedup/타인 403) + get(최신 상태) + prune.

httpx ASGITransport + 실 SQLAlchemy 레포(SQLite, tests/integration/conftest.py 의
schema_translate_map에 ms 추가돼 있음) — doc 소유권 테스트(test_doc_ownership_e2e.py)와
동일하게 token_issuer() 로 직접 토큰을 발급해 두 계정을 흉내낸다(SQLite는 FK 강제 안 함).
"""
import hashlib
import uuid

import pytest
from sqlalchemy import select
from src.features.auth.presentation.dependencies import token_issuer
from src.infrastructure.db.models.manuscript import ManuscriptRevision


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@pytest.fixture
def tokens():
    issuer = token_issuer()
    return {
        "A": issuer.issue(uuid.uuid4(), "AUTHOR"),
        "B": issuer.issue(uuid.uuid4(), "AUTHOR"),
    }


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _chapter(key="ch-1", title="1장", html="<p>본문</p>"):
    return {"chapterKey": key, "title": title, "html": html, "contentHash": _hash(html)}


async def _push(c, sync_key, chapters, headers, title="제목 없는 책"):
    return await c.put(f"/api/manuscripts/{sync_key}", json={"title": title, "chapters": chapters}, headers=headers)


# ── push: 생성 + 저장 ────────────────────────────────────────────


async def test_push_requires_auth(client):
    sync_key = str(uuid.uuid4())
    r = await _push(client, sync_key, [_chapter()], headers={})
    assert r.status_code == 401


async def test_push_creates_book_and_saves_new_chapter(client, tokens):
    sync_key = str(uuid.uuid4())
    r = await _push(client, sync_key, [_chapter()], _auth(tokens["A"]))
    assert r.status_code == 200, r.text
    assert r.json() == {"savedCount": 1, "skippedCount": 0}


async def test_push_same_sync_key_reuses_book_no_recreate(client, tokens):
    sync_key = str(uuid.uuid4())
    await _push(client, sync_key, [_chapter(html="<p>v1</p>")], _auth(tokens["A"]), title="1판")
    r = await _push(client, sync_key, [_chapter(html="<p>v2</p>")], _auth(tokens["A"]), title="2판")
    assert r.json() == {"savedCount": 1, "skippedCount": 0}

    state = (await client.get(f"/api/manuscripts/{sync_key}", headers=_auth(tokens["A"]))).json()
    assert state["title"] == "2판"  # 제목도 최신으로 갱신(touch_book)


# ── dedup ────────────────────────────────────────────────────────


async def test_push_dedup_skips_when_hash_unchanged(client, tokens):
    sync_key = str(uuid.uuid4())
    same_chapter = _chapter(html="<p>변화 없음</p>")
    await _push(client, sync_key, [same_chapter], _auth(tokens["A"]))

    r = await _push(client, sync_key, [same_chapter], _auth(tokens["A"]))
    assert r.json() == {"savedCount": 0, "skippedCount": 1}


async def test_push_mixed_chapters_dedup_independently(client, tokens):
    sync_key = str(uuid.uuid4())
    unchanged = _chapter(key="ch-1", html="<p>그대로</p>")
    changed_v1 = _chapter(key="ch-2", html="<p>v1</p>")
    await _push(client, sync_key, [unchanged, changed_v1], _auth(tokens["A"]))

    changed_v2 = _chapter(key="ch-2", html="<p>v2</p>")
    r = await _push(client, sync_key, [unchanged, changed_v2], _auth(tokens["A"]))
    assert r.json() == {"savedCount": 1, "skippedCount": 1}


# ── 타인 소유 책 — 403 ────────────────────────────────────────────


async def test_push_to_others_sync_key_returns_403(client, tokens):
    sync_key = str(uuid.uuid4())
    await _push(client, sync_key, [_chapter()], _auth(tokens["A"]))

    r = await _push(client, sync_key, [_chapter()], _auth(tokens["B"]))
    assert r.status_code == 403


async def test_get_others_manuscript_returns_403(client, tokens):
    sync_key = str(uuid.uuid4())
    await _push(client, sync_key, [_chapter()], _auth(tokens["A"]))

    r = await client.get(f"/api/manuscripts/{sync_key}", headers=_auth(tokens["B"]))
    assert r.status_code == 403


async def test_get_unknown_sync_key_returns_404(client, tokens):
    r = await client.get(f"/api/manuscripts/{uuid.uuid4()}", headers=_auth(tokens["A"]))
    assert r.status_code == 404


# ── get: 챕터별 최신 상태 ──────────────────────────────────────────


async def test_get_manuscript_returns_latest_revision_per_chapter(client, tokens):
    sync_key = str(uuid.uuid4())
    await _push(
        client, sync_key,
        [_chapter(key="ch-1", title="1장", html="<p>1장 v1</p>")],
        _auth(tokens["A"]),
    )
    await _push(
        client, sync_key,
        [_chapter(key="ch-1", title="1장", html="<p>1장 v2</p>"), _chapter(key="ch-2", title="2장", html="<p>2장</p>")],
        _auth(tokens["A"]),
    )

    state = (await client.get(f"/api/manuscripts/{sync_key}", headers=_auth(tokens["A"]))).json()
    by_key = {c["chapterKey"]: c for c in state["chapters"]}
    assert len(by_key) == 2
    assert by_key["ch-1"]["html"] == "<p>1장 v2</p>"  # 최신 리비전만, v1은 안 보임
    assert by_key["ch-2"]["html"] == "<p>2장</p>"


# ── prune: 챕터당 50개 초과 ────────────────────────────────────────


async def test_revision_prune_caps_at_50_per_chapter(client, tokens, sessionmaker):
    sync_key = str(uuid.uuid4())
    for i in range(55):
        r = await _push(client, sync_key, [_chapter(key="ch-1", html=f"<p>v{i}</p>")], _auth(tokens["A"]))
        assert r.status_code == 200, r.text

    async with sessionmaker() as s:
        rows = (
            await s.execute(select(ManuscriptRevision).where(ManuscriptRevision.chapter_key == "ch-1"))
        ).scalars().all()
        assert len(rows) == 50

    # 가장 최근 것들만 남아야 한다 — v54(마지막 push)가 살아있고 v0(가장 오래됨)은 pruned.
    state = (await client.get(f"/api/manuscripts/{sync_key}", headers=_auth(tokens["A"]))).json()
    assert state["chapters"][0]["html"] == "<p>v54</p>"
