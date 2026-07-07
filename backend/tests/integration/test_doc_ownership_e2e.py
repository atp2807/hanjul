"""doc 소유권 매트릭스 — 전 계층 E2E (httpx ASGITransport + 실 레포/SQLite). (juldoc test_ownership 이식)

점진 잠금 계약:
- ownerless(비로그인 생성) 문서 = 종전 동작(누구나 수정·삭제·공유).
- owned 문서 = 소유자만 save/delete/export/share; 타인·미인증은 403.
- list: 로그인 = 내 문서 + ownerless, 비로그인 = ownerless 만.
- 공유 링크 공개 접근(/api/shares/{token})은 소유권 무관(링크가 자격).
- API 응답은 owner_id 대신 mine: bool.

juldoc 대비: 응답 스키마가 camelCase(mine 그대로), 에러 바디는 {"detail": …}(error_code 없음).
FK 미enforce SQLite 라 임의 계정 UUID 로 토큰을 발급해 소유자를 흉내낸다(계정 저장소 무관).
"""
import io
import uuid

import pytest
from src.features.auth.presentation.dependencies import token_issuer


@pytest.fixture
def tokens():
    issuer = token_issuer()
    return {
        "A": issuer.issue(uuid.uuid4(), "READER"),
        "B": issuer.issue(uuid.uuid4(), "READER"),
    }


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


async def _create(c, title, headers=None):
    r = await c.post("/api/documents", json={"title": title}, headers=headers or {})
    return r.json()["id"]


async def _save(c, doc_id, html, headers=None):
    return await c.put(
        f"/api/documents/{doc_id}/html", json={"html": html}, headers=headers or {}
    )


async def _issue_share(c, doc_id, cap, headers=None):
    return await c.post(
        f"/api/documents/{doc_id}/shares", json={"capability": cap}, headers=headers or {}
    )


# ── owned 문서 잠금 ────────────────────────────────────────────


async def test_owner_can_save_others_cannot(client, tokens):
    doc_id = await _create(client, "A's doc", _auth(tokens["A"]))
    assert (await _save(client, doc_id, "<p>x</p>", _auth(tokens["A"]))).status_code == 200
    assert (await _save(client, doc_id, "<p>y</p>", _auth(tokens["B"]))).status_code == 403
    assert (await _save(client, doc_id, "<p>z</p>")).status_code == 403


async def test_owner_can_delete_others_cannot(client, tokens):
    doc_id = await _create(client, "A's doc", _auth(tokens["A"]))
    assert (await client.delete(f"/api/documents/{doc_id}", headers=_auth(tokens["B"]))).status_code == 403
    assert (await client.delete(f"/api/documents/{doc_id}")).status_code == 403
    assert (await client.delete(f"/api/documents/{doc_id}", headers=_auth(tokens["A"]))).status_code == 200


async def test_owner_can_export_others_cannot(client, tokens):
    doc_id = await _create(client, "A's doc", _auth(tokens["A"]))
    base = f"/api/documents/{doc_id}/export/epub"
    assert (await client.get(base, headers=_auth(tokens["B"]))).status_code == 403
    assert (await client.get(base)).status_code == 403
    assert (await client.get(base, headers=_auth(tokens["A"]))).status_code == 200


async def test_owner_can_share_others_cannot(client, tokens):
    doc_id = await _create(client, "A's doc", _auth(tokens["A"]))
    assert (await _issue_share(client, doc_id, "view", _auth(tokens["B"]))).status_code == 403
    assert (await _issue_share(client, doc_id, "view")).status_code == 403
    assert (await _issue_share(client, doc_id, "view", _auth(tokens["A"]))).status_code == 201


async def test_owner_can_revoke_others_cannot(client, tokens):
    doc_id = await _create(client, "A's doc", _auth(tokens["A"]))
    share_id = (await _issue_share(client, doc_id, "view", _auth(tokens["A"]))).json()["id"]
    assert (await client.delete(f"/api/shares/{share_id}", headers=_auth(tokens["B"]))).status_code == 403
    assert (await client.delete(f"/api/shares/{share_id}", headers=_auth(tokens["A"]))).status_code == 204


async def test_owner_can_list_shares_others_cannot(client, tokens):
    # 보안 회귀 가드: 토큰 목록 = 살아있는 접근 자격 전량 — 타인/미인증이 긁으면 잠금 우회.
    doc_id = await _create(client, "A's doc", _auth(tokens["A"]))
    await _issue_share(client, doc_id, "edit", _auth(tokens["A"]))
    url = f"/api/documents/{doc_id}/shares"
    other = await client.get(url, headers=_auth(tokens["B"]))
    assert other.status_code == 403
    assert "items" not in other.json()  # 토큰이 새지 않는다
    assert (await client.get(url)).status_code == 403
    mine = await client.get(url, headers=_auth(tokens["A"]))
    assert mine.status_code == 200
    assert mine.json()["total"] == 1


# ── ownerless 문서 = 종전 동작 ──────────────────────────────────


async def test_anon_created_doc_editable_by_anyone(client, tokens):
    doc_id = await _create(client, "public doc")
    assert (await _save(client, doc_id, "<p>x</p>")).status_code == 200
    assert (await _save(client, doc_id, "<p>y</p>", _auth(tokens["B"]))).status_code == 200
    assert (await _issue_share(client, doc_id, "view")).status_code == 201
    assert (await client.delete(f"/api/documents/{doc_id}", headers=_auth(tokens["B"]))).status_code == 200


async def test_anon_can_list_shares_of_ownerless_doc(client, tokens):
    doc_id = await _create(client, "public doc")
    await _issue_share(client, doc_id, "view")
    url = f"/api/documents/{doc_id}/shares"
    assert (await client.get(url)).status_code == 200
    assert (await client.get(url, headers=_auth(tokens["B"]))).status_code == 200


async def test_upload_while_anon_is_ownerless(client, tokens):
    r = await client.post(
        "/api/documents/upload",
        files={"file": ("a.md", io.BytesIO(b"# Hi"), "text/markdown")},
    )
    doc_id = r.json()["id"]
    assert (await _save(client, doc_id, "<p>x</p>", _auth(tokens["A"]))).status_code == 200


# ── 목록 가시성 ────────────────────────────────────────────────


async def test_login_sees_own_plus_ownerless_others_hidden(client, tokens):
    a_doc = await _create(client, "A doc", _auth(tokens["A"]))
    b_doc = await _create(client, "B doc", _auth(tokens["B"]))
    public = await _create(client, "public doc")
    listing = (await client.get("/api/documents", headers=_auth(tokens["A"]))).json()
    a_ids = {d["id"] for d in listing["items"]}
    assert a_doc in a_ids
    assert public in a_ids
    assert b_doc not in a_ids


async def test_anon_sees_only_ownerless(client, tokens):
    a_doc = await _create(client, "A doc", _auth(tokens["A"]))
    public = await _create(client, "public doc")
    anon_ids = {d["id"] for d in (await client.get("/api/documents")).json()["items"]}
    assert public in anon_ids
    assert a_doc not in anon_ids


# ── mine 플래그 ────────────────────────────────────────────────


async def test_mine_true_for_owner_false_for_ownerless(client, tokens):
    owned = await _create(client, "owned", _auth(tokens["A"]))
    public = await _create(client, "public")
    owned_doc = (await client.get(f"/api/documents/{owned}", headers=_auth(tokens["A"]))).json()
    public_doc = (await client.get(f"/api/documents/{public}", headers=_auth(tokens["A"]))).json()
    assert owned_doc["mine"] is True
    assert public_doc["mine"] is False
    assert "ownerId" not in owned_doc and "owner_id" not in owned_doc


async def test_mine_false_for_other_viewer(client, tokens):
    owned = await _create(client, "owned", _auth(tokens["A"]))
    doc = (await client.get(f"/api/documents/{owned}", headers=_auth(tokens["B"]))).json()
    assert doc["mine"] is False


# ── 공유 링크 공개 접근 = 소유권 무관 ────────────────────────────


async def test_share_token_view_works_without_auth(client, tokens):
    doc_id = await _create(client, "A's shared doc", _auth(tokens["A"]))
    await _save(client, doc_id, "<p>secret body</p>", _auth(tokens["A"]))
    token = (await _issue_share(client, doc_id, "view", _auth(tokens["A"]))).json()["token"]
    meta = await client.get(f"/api/shares/{token}")
    assert meta.status_code == 200
    assert meta.json()["title"] == "A's shared doc"
    html = await client.get(f"/api/shares/{token}/html")
    assert html.status_code == 200
    assert "secret body" in html.text


async def test_edit_share_saves_without_auth_for_owned_doc(client, tokens):
    doc_id = await _create(client, "A doc", _auth(tokens["A"]))
    token = (await _issue_share(client, doc_id, "edit", _auth(tokens["A"]))).json()["token"]
    resp = await client.put(f"/api/shares/{token}/html", json={"html": "<p>via link</p>"})
    assert resp.status_code == 204


async def test_export_share_downloads_without_auth_for_owned_doc(client, tokens):
    doc_id = await _create(client, "A doc", _auth(tokens["A"]))
    token = (await _issue_share(client, doc_id, "export", _auth(tokens["A"]))).json()["token"]
    resp = await client.get(f"/api/shares/{token}/export/epub")
    assert resp.status_code == 200
    assert resp.content[:2] == b"PK"
