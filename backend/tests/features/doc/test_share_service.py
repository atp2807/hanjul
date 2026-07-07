"""ShareService 유스케이스 테스트 — InMemory repos, 반환값·관측 상태로 검증. (juldoc 이식)"""
import uuid

import pytest
from src.features.doc.application.document_service import DocumentService
from src.features.doc.application.share_service import ShareService
from src.features.doc.domain.models import (
    Capability,
    DocumentNotFound,
    ShareCapabilityDenied,
    ShareNotFound,
    UnknownCapability,
)

from tests.fixtures.fake_doc_repo import FakeDocumentRepo, FakeShareRepo


@pytest.fixture
def documents() -> DocumentService:
    return DocumentService(FakeDocumentRepo())


@pytest.fixture
def shares(documents) -> ShareService:
    return ShareService(FakeShareRepo(), documents)


async def _doc(documents: DocumentService, title: str = "Doc"):
    return await documents.create_empty(title)


class TestCreateShare:
    async def test_issue_view_returns_token_and_url(self, shares, documents):
        doc = await _doc(documents)
        link = await shares.create_share(doc.id, "view")
        assert link.capability is Capability.VIEW
        assert link.token
        assert link.revoked is False
        assert link.document_id == doc.id

    async def test_issue_edit(self, shares, documents):
        doc = await _doc(documents)
        link = await shares.create_share(doc.id, "edit")
        assert link.capability is Capability.EDIT

    async def test_tokens_are_unique_per_issue(self, shares, documents):
        doc = await _doc(documents)
        a = await shares.create_share(doc.id, "view")
        b = await shares.create_share(doc.id, "view")
        assert a.token != b.token

    async def test_issue_export_allowed(self, shares, documents):
        doc = await _doc(documents)
        link = await shares.create_share(doc.id, "export")
        assert link.capability is Capability.EXPORT
        assert link.revoked is False

    async def test_issue_unknown_capability_rejected_422(self, shares, documents):
        doc = await _doc(documents)
        with pytest.raises(UnknownCapability) as ei:
            await shares.create_share(doc.id, "bogus")
        assert ei.value.status_code == 422

    async def test_issue_for_missing_document_404(self, shares):
        with pytest.raises(DocumentNotFound):
            await shares.create_share(uuid.uuid4(), "view")


class TestListShares:
    async def test_list_includes_revoked(self, shares, documents):
        doc = await _doc(documents)
        keep = await shares.create_share(doc.id, "view")
        gone = await shares.create_share(doc.id, "edit")
        await shares.revoke_share(gone.id)
        items, total = await shares.list_shares(doc.id, page=1, page_size=50)
        assert total == 2
        by_id = {s.id: s for s in items}
        assert by_id[keep.id].revoked is False
        assert by_id[gone.id].revoked is True

    async def test_list_scoped_to_document(self, shares, documents):
        doc_a = await _doc(documents, "A")
        doc_b = await _doc(documents, "B")
        await shares.create_share(doc_a.id, "view")
        _, total_b = await shares.list_shares(doc_b.id, 1, 50)
        assert total_b == 0


class TestRevoke:
    async def test_revoke_is_idempotent(self, shares, documents):
        doc = await _doc(documents)
        link = await shares.create_share(doc.id, "view")
        await shares.revoke_share(link.id)
        await shares.revoke_share(link.id)  # 두 번째도 예외 없이 성공(멱등)
        items, _ = await shares.list_shares(doc.id, 1, 50)
        assert items[0].revoked is True

    async def test_revoke_missing_is_noop(self, shares):
        await shares.revoke_share(uuid.uuid4())  # 없는 share_id 회수도 조용히 성공

    async def test_revoked_link_access_returns_404(self, shares, documents):
        doc = await _doc(documents)
        link = await shares.create_share(doc.id, "view")
        await shares.revoke_share(link.id)
        with pytest.raises(ShareNotFound):
            await shares.get_share_html(link.token)

    async def test_no_reactivation_after_revoke(self, shares, documents):
        doc = await _doc(documents)
        link = await shares.create_share(doc.id, "view")
        await shares.revoke_share(link.id)
        with pytest.raises(ShareNotFound):
            await shares.get_share_meta(link.token)


class TestPublicAccess:
    async def test_meta_returns_title_and_capability(self, shares, documents):
        doc = await _doc(documents, "My Title")
        link = await shares.create_share(doc.id, "view")
        title, cap = await shares.get_share_meta(link.token)
        assert title == "My Title"
        assert cap is Capability.VIEW

    async def test_missing_token_returns_404(self, shares):
        with pytest.raises(ShareNotFound) as ei:
            await shares.get_share_meta("nonexistent-token")
        assert ei.value.status_code == 404

    async def test_view_html_is_canonical(self, shares, documents):
        doc = await _doc(documents)
        await documents.save_html(doc.id, "<p>hello</p>")
        link = await shares.create_share(doc.id, "view")
        html = await shares.get_share_html(link.token)
        assert html == '<article data-juldoc="1"><p>hello</p></article>'

    async def test_soft_deleted_document_returns_404(self, shares, documents):
        doc = await _doc(documents)
        link = await shares.create_share(doc.id, "view")
        await documents.delete_document(doc.id)
        with pytest.raises(ShareNotFound):
            # 문서 삭제도 부재/회수와 동일하게 은닉(DocumentNotFound 누출 금지).
            await shares.get_share_html(link.token)


class TestSaveViaShare:
    async def test_view_link_put_forbidden_403(self, shares, documents):
        doc = await _doc(documents)
        link = await shares.create_share(doc.id, "view")
        with pytest.raises(ShareCapabilityDenied) as ei:
            await shares.save_share_html(link.token, "<p>x</p>")
        assert ei.value.status_code == 403

    async def test_edit_link_saves_canonical(self, shares, documents):
        doc = await _doc(documents)
        link = await shares.create_share(doc.id, "edit")
        await shares.save_share_html(link.token, "<p>edited via share</p>")
        stored = await documents.get_html(doc.id)
        assert stored == '<article data-juldoc="1"><p>edited via share</p></article>'

    async def test_edit_link_put_sanitizes_xss(self, shares, documents):
        # 저장형 XSS 회귀(필수): 공유 저장 경로도 문서와 동일 정화 왕복을 반드시 통과.
        doc = await _doc(documents)
        link = await shares.create_share(doc.id, "edit")
        payload = '<p>hi</p><img src=x onerror="alert(1)"><script>alert(2)</script>'
        await shares.save_share_html(link.token, payload)
        stored = await documents.get_html(doc.id)
        assert "onerror" not in stored
        assert "<script" not in stored
        assert "alert(1)" not in stored
        assert "alert(2)" not in stored
        assert "<p>hi</p>" in stored

    async def test_revoked_edit_link_put_returns_404(self, shares, documents):
        doc = await _doc(documents)
        link = await shares.create_share(doc.id, "edit")
        await shares.revoke_share(link.id)
        with pytest.raises(ShareNotFound):
            await shares.save_share_html(link.token, "<p>x</p>")


class TestExportViaShare:
    async def test_export_link_returns_title_and_epub(self, shares, documents):
        doc = await _doc(documents, "Exportable")
        link = await shares.create_share(doc.id, "export")
        title, data = await shares.export_epub(link.token)
        assert title == "Exportable"
        assert data[:2] == b"PK"

    async def test_view_link_export_forbidden_403(self, shares, documents):
        doc = await _doc(documents)
        link = await shares.create_share(doc.id, "view")
        with pytest.raises(ShareCapabilityDenied) as ei:
            await shares.export_epub(link.token)
        assert ei.value.status_code == 403

    async def test_edit_link_export_forbidden_403(self, shares, documents):
        # EDIT⊥EXPORT — 편집 링크로 export 불가.
        doc = await _doc(documents)
        link = await shares.create_share(doc.id, "edit")
        with pytest.raises(ShareCapabilityDenied):
            await shares.export_epub(link.token)

    async def test_export_link_can_also_view(self, shares, documents):
        # VIEW ⊂ EXPORT — export 링크는 meta/html 열람도 가능.
        doc = await _doc(documents, "V")
        link = await shares.create_share(doc.id, "export")
        title, cap = await shares.get_share_meta(link.token)
        assert title == "V"
        assert cap is Capability.EXPORT
        html = await shares.get_share_html(link.token)
        assert 'data-juldoc="1"' in html

    async def test_export_link_cannot_edit(self, shares, documents):
        doc = await _doc(documents)
        link = await shares.create_share(doc.id, "export")
        with pytest.raises(ShareCapabilityDenied):
            await shares.save_share_html(link.token, "<p>x</p>")

    async def test_revoked_export_link_returns_404(self, shares, documents):
        doc = await _doc(documents)
        link = await shares.create_share(doc.id, "export")
        await shares.revoke_share(link.id)
        with pytest.raises(ShareNotFound):
            await shares.export_epub(link.token)

    async def test_export_missing_token_returns_404(self, shares):
        with pytest.raises(ShareNotFound):
            await shares.export_epub("no-such-token")

    async def test_export_soft_deleted_document_returns_404(self, shares, documents):
        doc = await _doc(documents)
        link = await shares.create_share(doc.id, "export")
        await documents.delete_document(doc.id)
        with pytest.raises(ShareNotFound):
            await shares.export_epub(link.token)
