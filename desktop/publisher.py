"""한줄 IDE P1 슬라이스 4 — 발행 연결. 로컬(SQLite) 책을 hanjul 백엔드 출판 API로
밀어넣고 즉시출판한다. 인증은 이 슬라이스에선 토큰 수동 설정(OAuth는 다음 슬라이스).

실측 근거(2026-07-08, file:line 인용) — 서버 계약:
- 책 생성 `POST /api/books` — body `{title, kind="BOOK", language="ko"}`, 201 응답
  `{"bookId": <uuid>}` (backend/src/features/books/presentation/endpoints.py:32-43,
  schemas.py:7-14 `CreateBookRequest`/`CreateBookResponse`). 웹 클라 선례:
  `web/src/services/api/books.js:10-12` `createBook(title, kind='BOOK')`.
- 정본 전체 교체 `PUT /api/books/{id}/content` — body
  `{"chapters":[{"title","blocks":[{"type","html"}]}]}`, 204 무응답
  (endpoints.py:72-85, schemas.py:27-39 `BlockInput`/`ChapterInput`/`SetContentRequest`).
  `type` ∈ P|H1|H2|H3|QUOTE|HR (schemas.py:28 주석). 웹 선례: books.js:71-73
  `setBookContent()`, `WritePage.jsx:154-156` splitIntoChapters→setBookContent→publishNow.
- 즉시출판 `POST /api/books/{id}/publish-now` — body 없음, 204 무응답
  (catalog/presentation/endpoints.py:144-158). **가격 필수** —
  `catalog/application/catalog_service.py:89-94` `auto_publish()`가 `price_amt is None`
  이면 `PriceRequired`(catalog/domain/models.py:51-54, →422 "출판하려면 가격을 먼저
  설정해야 해요.")를 던진다 — 본문 형식 위반(422 "본문 형식이 올바르지 않아요.")과는
  별개의 실패 사유다. 이 슬라이스는 가격 설정 UI를 만들지 않으므로(스펙 밖) 이 422 는
  그대로 표면화한다 — 아래 "미해결" 참고.
  실제 API 경로는 `books.js` 가 아니라 catalog 라우터 소속(`endpoints.py:1` "출판
  라이프사이클(/books) + 스토어(/store)") — prefix 없이 `/books/...` 그대로.
- 인증 — `Authorization: Bearer <token>` (`get_current_account`,
  auth/presentation/dependencies.py:43-50 `HTTPBearer`). 모든 도메인 에러는
  `{"detail": <str>}` 로 통일(`main.py:111-114` `_domain_error_handler`).
- 전체 API prefix `/api` — `src/presentation/api.py:33` `APIRouter(prefix="/api")`.
  웹 클라 조립: `packages/lib/src/apiClient.js:33` `fetch(`${BASE}/api${path}`, ...)`.

⚠️ 서버 화이트리스트(lr-385e5cc2) — 클라이언트 프리플라이트 필수:
`backend/src/engine/imports/block_html.py:76-91` `validate_block_html(block_type, html)`
가 P|H1|H2|H3|QUOTE 외곽 태그(무속성) + 내부 strong/em(무속성) + `<hr/>` 만 허용한다.
이 모듈은 **같은 함수를 그대로 import**(drift 0) — 새 검증기를 만들지 않는다. 위반이면
`InvalidBlockHtml`. 서버(`book_service.py:54-60`)는 위반 시 이유를 감추고 그냥
"본문 형식이 올바르지 않아요."(422)만 돌려주므로, "몇 장 어떤 블록이 왜 위반인지"를
보여주는 건 **이 클라이언트 프리플라이트가 유일한 자리**다 — 조용히 벗겨내지 않고
발행 자체를 막는다(네트워크 호출 0회).

packages/doc 에디터는 표(TABLE)·이미지(IMAGE)·목록(LIST)·코드(CODE) 블록과 H4~H6,
그리고 인라인 `<u>`/`<a href>`(dialect.py:16 "strong/em/u/a" 인라인 화이트리스트,
block_html.py:15 는 strong/em 만)까지 만들 수 있어 서버 화이트리스트보다 넓다 — 이
모듈은 그 초과분을 전부 "미지원 블록"으로 그대로 넘겨 validate_block_html 이
"알 수 없는 블록 타입"으로 거부하게 한다(_block_type 참고).

h1 경계 유지: 로컬 챕터 하나의 html 안에 h1 이 더 있으면(가져오기로 여러 절을 합친
경우 등) `importer.py:119 _split_by_h1`(원고 가져오기가 이미 쓰는 동일 함수)을 그대로
재사용해 서버 챕터 여러 개로 추가 분리한다 — web Writer 의
`web/src/writer/core/chapters.js:7-26 splitIntoChapters`(h1=챕터 경계, h2/h3는 본문에
잔존)와 동일 규칙.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from src.engine.doc.dialect import parse_dialect, serialize_doc  # noqa: E402
from src.engine.doc.models import BlockType, Page, UniversalDoc  # noqa: E402
from src.engine.imports.block_html import InvalidBlockHtml, validate_block_html  # noqa: E402

from importer import _split_by_h1  # noqa: E402  (h1 경계 분리 재사용 — importer.py:119)

_ARTICLE_OPEN = '<article data-juldoc="1">'
_ARTICLE_CLOSE = "</article>"

# HEADING 레벨 → 서버 정본 타입. level==1 은 _split_by_h1 이 챕터 경계로 이미 소비하므로
# 그룹 내부 블록엔 이론상 도달하지 않는다(방어적으로만 포함).
_HEADING_TYPE = {1: "H1", 2: "H2", 3: "H3"}


class PublishHttpError(Exception):
    """서버가 4xx/5xx 로 응답했거나 연결 자체가 실패함. status=None 이면 연결 실패."""

    def __init__(self, status, detail):
        super().__init__(f"HTTP {status}: {detail}")
        self.status = status
        self.detail = detail


def _block_html(block) -> str:
    """UniversalDoc Block 하나를 dialect 의 실제 직렬화 그대로 outer-html 로 만든다.

    수제 문자열 조립 대신 `serialize_doc`(dialect.py:417 — importer.py 도 재사용 중인
    동일 함수)을 단일 블록짜리 문서에 호출해 article 래퍼만 벗긴다. style 속성이 붙은
    `<p style="...">`나 TABLE/IMAGE/LIST/CODE 같은 서버 미지원 태그까지 "실제로 서버에
    보낼 html"과 100% 동일하게 얻어야 프리플라이트가 진짜 위반을 놓치지 않는다(수제
    재구성은 위반을 조용히 빠뜨릴 위험이 있다).
    """
    wrapped = serialize_doc(UniversalDoc(pages=[Page(blocks=[block])]))
    return wrapped[len(_ARTICLE_OPEN):-len(_ARTICLE_CLOSE)]


def _block_type(block) -> str:
    """서버 정본 타입 코드로 매핑.

    PARAGRAPH→P, QUOTE→QUOTE, HEADING(level 2/3)→H2/H3 만 서버가 아는 타입이고, 그 외
    (CODE/IMAGE/LIST/TABLE, HEADING level 1·4~6)는 엔진 타입명을 그대로 넘겨
    `validate_block_html` 이 "알 수 없는 블록 타입"(block_html.py:85-87)으로 명시적으로
    거부하게 한다 — 조용히 벗겨내지 않는다.
    """
    if block.type == BlockType.HEADING:
        level = int(block.meta.get("level", 1))
        return _HEADING_TYPE.get(level, f"H{level}")
    if block.type == BlockType.PARAGRAPH:
        return "P"
    if block.type == BlockType.QUOTE:
        return "QUOTE"
    return block.type.value  # CODE|IMAGE|LIST|TABLE → 서버가 모르는 타입, 의도적으로 그대로 전달


def _local_chapter_to_server_chapters(title: str, html: str) -> list[dict]:
    """로컬(SQLite) 챕터 1개(title, `<article data-juldoc="1">` html) → 서버
    ChapterInput 후보 목록(검증 전). h1 경계마다 별도 챕터로 쪼갠다(모듈 docstring 참고).

    반환: ``[{"title": str, "blocks": [{"type","html"}, ...]}, ...]`` (최소 1개).
    """
    doc = parse_dialect(html)
    blocks = [b for page in doc.pages for b in page.blocks]
    groups = _split_by_h1(blocks)

    server_chapters = []
    for i, (group_title, group_blocks) in enumerate(groups):
        # _split_by_h1 은 첫 그룹(h1 이전)에서만 title=None 을 낼 수 있다 — 그 경우
        # 로컬 챕터 자신의 제목을 쓴다(가져오기의 "파일명 스템" 대신).
        chapter_title = title if (i == 0 and group_title is None) else group_title
        server_chapters.append(
            {
                "title": chapter_title,
                "blocks": [
                    {"type": _block_type(b), "html": _block_html(b)} for b in group_blocks
                ],
            }
        )
    return server_chapters


def preflight(store) -> tuple[bool, list[dict] | None, list[dict]]:
    """로컬 챕터 전부를 서버 계약 형태로 변환 + `validate_block_html` 로 검증.

    반환: ``(ok, server_chapters_or_None, violations)``. 위반이 하나라도 있으면
    ``server_chapters`` 는 ``None``(부분 발행 없음 — 네트워크 호출은 이 함수 안에서 전혀
    일어나지 않는다). violations 항목:
    ``{"chapterTitle", "blockIndex", "blockType", "reason"}``.
    """
    server_chapters: list[dict] = []
    violations: list[dict] = []

    for summary in store.list_chapters():
        full = store.load_chapter(summary["id"])
        for group in _local_chapter_to_server_chapters(full["title"], full["html"]):
            for idx, block in enumerate(group["blocks"]):
                try:
                    validate_block_html(block["type"], block["html"])
                except InvalidBlockHtml as exc:
                    violations.append(
                        {
                            "chapterTitle": group["title"],
                            "blockIndex": idx,
                            "blockType": block["type"],
                            "reason": str(exc),
                        }
                    )
            server_chapters.append(group)

    if violations:
        return False, None, violations
    return True, server_chapters, []


def _api_base(settings: dict | None) -> str:
    return ((settings or {}).get("apiBase") or "").rstrip("/")


def _request(settings: dict | None, method: str, path: str, body=None):
    """urllib(stdlib) 기반 호출 — `{apiBase}/api{path}`, Bearer 토큰, JSON body.

    반환: (status, parsed_json_or_None). 4xx/5xx·연결 실패는 PublishHttpError.
    """
    url = f"{_api_base(settings)}/api{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    token = (settings or {}).get("token")
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            parsed = json.loads(raw.decode("utf-8")) if raw else None
            return resp.status, parsed
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        detail = None
        if raw:
            try:
                parsed = json.loads(raw.decode("utf-8"))
                detail = parsed.get("detail") if isinstance(parsed, dict) else parsed
            except json.JSONDecodeError:
                detail = raw.decode("utf-8", errors="replace")
        raise PublishHttpError(exc.code, detail) from None
    except urllib.error.URLError as exc:
        raise PublishHttpError(None, str(exc.reason)) from None


def publish(store, settings: dict | None) -> dict:
    """로컬 책 전체를 서버로 발행(신규면 생성 후 remote_book_id 저장) + 즉시출판.

    1. 프리플라이트 — 위반 있으면 네트워크 호출 없이
       ``{"ok": False, "violations": [...]}``.
    2. remote_book_id 없으면 `POST /books` 로 생성 후 store 에 저장.
    3. `PUT /books/{id}/content` → `POST /books/{id}/publish-now`.
    4. HTTP 실패(연결 실패 포함)는 ``{"ok": False, "error": {"status", "message"}}``
       — 특히 가격 미설정이면 서버가 422("가격을 먼저 정하세요" 부류)를 그대로 돌려준다
       (이 슬라이스는 가격 설정 UI가 없다 — 모듈 docstring "미해결" 참고).
    """
    ok, server_chapters, violations = preflight(store)
    if not ok:
        return {"ok": False, "violations": violations}

    try:
        remote_book_id = store.get_remote_book_id()
        if not remote_book_id:
            book = store.get_book()
            _, created = _request(
                settings, "POST", "/books", {"title": book["title"], "kind": "BOOK"}
            )
            remote_book_id = created["bookId"]
            store.set_remote_book_id(remote_book_id)

        _request(
            settings, "PUT", f"/books/{remote_book_id}/content", {"chapters": server_chapters}
        )
        _request(settings, "POST", f"/books/{remote_book_id}/publish-now")
    except PublishHttpError as exc:
        return {"ok": False, "error": {"status": exc.status, "message": exc.detail}}

    return {
        "ok": True,
        "remoteBookId": remote_book_id,
        "chapterCount": len(server_chapters),
    }
