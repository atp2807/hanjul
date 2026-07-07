"""SqlDocumentRepository/SqlShareRepository 통합 테스트 — 실 DB 엔진(SQLite)에 영속성 검증.

juldoc 의 Pg 전용(DATABASE_URL skipif) repo 테스트를 hanjul SQLAlchemy 통합테스트로 대체.
soft delete 필터·ownerless OR owner 가시성·최신순·토큰 조회·멱등 회수 의미를 실 DB 로 확인.
"""
import uuid
from datetime import UTC, datetime

from src.features.doc.domain.models import Capability, Document, ShareLink
from src.features.doc.infrastructure.doc_repo import (
    SqlDocumentRepository,
    SqlShareRepository,
)


def _doc(*, title="D", owner_id=None) -> Document:
    now = datetime.now(UTC)
    return Document(
        id=uuid.uuid4(),
        title=title,
        format="html",
        html='<article data-juldoc="1"></article>',
        source_hash=None,
        created_at=now,
        updated_at=now,
        owner_id=owner_id,
    )


async def test_create_get_roundtrip_and_soft_delete(sessionmaker):
    async with sessionmaker() as s:
        repo = SqlDocumentRepository(s)
        doc = await repo.create(_doc(title="한글문서"))

    async with sessionmaker() as s2:
        repo = SqlDocumentRepository(s2)
        fetched = await repo.get(doc.id)
        assert fetched is not None
        assert fetched.title == "한글문서"
        # soft delete → 이후 get None
        assert await repo.soft_delete(doc.id) is True
        assert await repo.get(doc.id) is None
        # 멱등: 이미 삭제된 대상 재삭제는 False
        assert await repo.soft_delete(doc.id) is False


async def test_update_html_skips_deleted(sessionmaker):
    async with sessionmaker() as s:
        repo = SqlDocumentRepository(s)
        doc = await repo.create(_doc())
        updated = await repo.update_html(doc.id, "<article>new</article>")
        assert updated is not None and updated.html == "<article>new</article>"
        await repo.soft_delete(doc.id)
        # 삭제된 문서 갱신은 None
        assert await repo.update_html(doc.id, "x") is None


async def test_list_visibility_ownerless_and_owner(sessionmaker):
    owner_a = uuid.uuid4()
    owner_b = uuid.uuid4()
    async with sessionmaker() as s:
        repo = SqlDocumentRepository(s)
        await repo.create(_doc(title="public", owner_id=None))
        await repo.create(_doc(title="A doc", owner_id=owner_a))
        await repo.create(_doc(title="B doc", owner_id=owner_b))

    async with sessionmaker() as s2:
        repo = SqlDocumentRepository(s2)
        # 비로그인: ownerless 만
        anon_items, anon_total = await repo.list(1, 50, viewer_id=None)
        assert anon_total == 1
        assert {d.title for d in anon_items} == {"public"}
        # 로그인 A: 내 문서 + ownerless (B 는 안 보임)
        a_items, a_total = await repo.list(1, 50, viewer_id=owner_a)
        assert a_total == 2
        assert {d.title for d in a_items} == {"public", "A doc"}


async def test_list_newest_first_and_pagination(sessionmaker):
    async with sessionmaker() as s:
        repo = SqlDocumentRepository(s)
        for i in range(3):
            d = _doc(title=f"doc-{i}")
            d.created_at = datetime(2026, 1, 1 + i, tzinfo=UTC)
            await repo.create(d)

    async with sessionmaker() as s2:
        repo = SqlDocumentRepository(s2)
        items, total = await repo.list(1, 2, viewer_id=None)
        assert total == 3
        assert [d.title for d in items] == ["doc-2", "doc-1"]  # 최신순


async def test_share_token_and_idempotent_revoke(sessionmaker):
    async with sessionmaker() as s:
        drepo = SqlDocumentRepository(s)
        doc = await drepo.create(_doc())
        srepo = SqlShareRepository(s)
        now = datetime.now(UTC)
        share = await srepo.create(
            ShareLink(
                id=uuid.uuid4(),
                document_id=doc.id,
                token="tok-abc",
                capability=Capability.EDIT,
                created_at=now,
            )
        )

    async with sessionmaker() as s2:
        srepo = SqlShareRepository(s2)
        by_token = await srepo.get_by_token("tok-abc")
        assert by_token is not None
        assert by_token.capability is Capability.EDIT
        assert by_token.revoked is False
        # 목록은 회수분 포함
        items, total = await srepo.list_by_document(share.document_id, 1, 50)
        assert total == 1
        # 멱등 회수 — 두 번 호출해도 revoked_ts 최초 1회
        await srepo.revoke(share.id)
        first = await srepo.get_by_id(share.id)
        await srepo.revoke(share.id)
        second = await srepo.get_by_id(share.id)
        assert first.revoked_at == second.revoked_at
        assert second.revoked is True
