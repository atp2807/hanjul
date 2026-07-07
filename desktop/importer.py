"""한줄 IDE P1 슬라이스 3 — 원고 가져오기(TXT/MD/DOCX/HWP/HWPX).

backend/src/engine/doc 의 순수 파이썬 파서를 그대로 재사용한다(dc-73539bba "Python 엔진
실소유 = 임포트 파서" — 파서를 새로 짜지 않는다). 각 포맷 파서로 UniversalDoc 을 얻고
`dialect.serialize_doc` 으로 `<article data-juldoc="1">` 래퍼 포함 정본 HTML 을 만든 뒤,
HEADING(level=1) 블록 경계로 챕터를 분리한다.

실측 근거(2026-07-08, file:line 인용):
- 파서 API — 텍스트 계열은 `Parser.parse(content: str) -> UniversalDoc`, 바이너리 계열은
  `BinaryParser.parse_bytes(content: bytes) -> UniversalDoc`
  (backend/src/engine/doc/parsers/base.py:9-15). `TextParser.parse`
  (parsers/text.py:9), `MarkdownParser.parse`(parsers/markdown.py:11),
  `DOCXParser.parse_bytes`(parsers/docx.py:350), `HWPParser.parse_bytes`
  (parsers/hwp.py:453), `HWPXParser.parse_bytes`(parsers/hwpx.py:257).
- `serialize_doc(doc: UniversalDoc) -> str` — backend/src/engine/doc/dialect.py:417.
  페이지를 flatten 해 `<article data-juldoc="1">...</article>` 래퍼로 감싼 정본 HTML을
  낸다(dialect.py:64-65 `_ARTICLE_OPEN`/`_ARTICLE_CLOSE`). 빈 UniversalDoc 도 빈 래퍼를
  낸다 — 이 모듈은 그 성질을 그대로 이용해 빈 챕터도 유효한 html을 갖게 한다.
- backend/src/features/doc/application/document_service.py:54-70 `upload_document()` 가
  바로 이 두 계층(포맷별 파서 → serialize_doc)을 업로드 경로에서 쓰는 실제 선례 —
  이 모듈은 그 패턴을 데스크탑에서 반복한다.
- HEADING 블록은 MarkdownParser(parsers/markdown.py:36-44, meta={"level": int})와
  DOCXParser(parsers/docx.py:315-328, meta={"level": int}, 스타일 기반)만 낸다.
  TextParser/HWPParser/HWPXParser 는 HEADING 을 전혀 만들지 않는다(세 파일 전체에
  `BlockType.HEADING` 미출현 — grep 실측) — 그래서 TXT/HWP/HWPX 파일은 h1 이 존재할 수
  없고 항상 "h1 없음 → 파일명 스템 제목의 챕터 1개" 경로를 탄다. 설계상 의도된 결과다.
- 서드파티 의존성 — 위 다섯 파서(text/markdown/docx/hwp/hwpx) 자체는 전부 stdlib만
  쓴다(zipfile/xml.etree.ElementTree/struct/zlib/re — parsers/docx.py:27-31,
  parsers/hwp.py:8-10, parsers/hwpx.py:12-14, parsers/markdown.py:3, parsers/text.py는
  import 없음). `desktop/requirements.txt` 변경 불필요.
  **주의**: `backend/src/engine/doc/ingest.py` 의 편의 함수 `ingest()`는 이 다섯 개 대신
  **10개 포맷 전부**(csv/html/pdf/pptx/xlsx 포함)를 무조건 import 한다(ingest.py:5-16,
  특히 8행 `from src.engine.doc.parsers.pdf import PDFParser`) — `PARSER_REGISTRY`가
  ingest.py:18-30, 포맷 판별 `detect_format`/`get_parser`가 ingest.py:36-48,
  `ingest(file_path)` 본체가 ingest.py:51-64. pdf.py:15 가 서드파티 `pdfminer`를 import 하므로
  `ingest()`를 그대로 가져오면 desktop 이 쓰지도 않는 PDF 파싱을 위해 pdfminer 를
  설치해야 한다(실측: `from importer import import_manuscript`만 해도
  `ModuleNotFoundError: No module named 'pdfminer'` 발생). 그래서 이 모듈은 `ingest()`를
  호출하지 않고 필요한 5개 파서 클래스만 직접 import 해 `_ingest()`에서
  `ingest.py:51-64`와 동일한 판별→호출→metadata 주입 패턴을 그대로 재현한다 — 파싱
  로직은 한 줄도 새로 짜지 않고, "전체 레지스트리를 강제로 다 부르는 계층"만 얇게
  건너뛴다.
- backend 내부 import 관례는 `from src.engine.doc.models import ...`
  (parsers/docx.py:33) — `src` 가 최상위 패키지로 잡히려면 sys.path 에 `backend/src`가
  아니라 `backend/`(= src/ 의 부모)를 넣어야 한다. 실측: backend/conftest.py:5
  `sys.path.insert(0, os.path.dirname(__file__))` — `__file__`이 `backend/conftest.py`이므로
  `os.path.dirname`은 `backend/` 그 자체다. 작업 지시서의 "sys.path에 backend/src 추가"
  문구는 이 실측과 어긋나 여기서 backend/ 를 넣는 쪽으로 정정한다(그래야
  `src.engine.doc...` import 가 실제로 동작한다).
"""
from __future__ import annotations

import re
import sys
from html import unescape
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from src.engine.doc.dialect import serialize_doc  # noqa: E402
from src.engine.doc.models import Block, BlockType, Page, UniversalDoc  # noqa: E402
from src.engine.doc.parsers.docx import DOCXParser  # noqa: E402
from src.engine.doc.parsers.hwp import HWPParser  # noqa: E402
from src.engine.doc.parsers.hwpx import HWPXParser  # noqa: E402
from src.engine.doc.parsers.markdown import MarkdownParser  # noqa: E402
from src.engine.doc.parsers.text import TextParser  # noqa: E402

_TAG_RE = re.compile(r"<[^>]+>")

# ingest.py:18-30(PARSER_REGISTRY)의 축소판 — 이 슬라이스가 지원하는 5개 포맷만.
_TEXT_PARSERS = {"txt": TextParser(), "md": MarkdownParser()}
_BINARY_PARSERS = {"docx": DOCXParser(), "hwp": HWPParser(), "hwpx": HWPXParser()}


def import_manuscript(path) -> list[dict]:
    """원고 파일을 파싱해 h1 경계로 분리한 챕터 목록을 반환한다.

    반환: ``[{"title": str, "html": str}, ...]`` — 최소 1개(빈 파일이거나 h1 이 전혀
    없으면 파일명 스템을 제목으로 쓰는 챕터 1개). ``html`` 은 각각
    ``<article data-juldoc="1">...</article>`` 래퍼를 유지한 정본.
    """
    file_path = Path(path)
    doc = _ingest(file_path)
    blocks = [block for page in doc.pages for block in page.blocks]
    groups = _split_by_h1(blocks)

    fallback_title = file_path.stem or "제목 없음"
    return [
        {
            "title": title if title is not None else fallback_title,
            "html": serialize_doc(UniversalDoc(pages=[Page(blocks=group_blocks)])),
        }
        for title, group_blocks in groups
    ]


def _ingest(file_path: Path) -> UniversalDoc:
    """backend/src/engine/doc/ingest.py:51-64 `ingest()`와 동일한 판별→파싱→metadata
    주입 패턴 — 다만 5개 포맷 로컬 레지스트리(`_TEXT_PARSERS`/`_BINARY_PARSERS`)만 쓴다
    (전체 10포맷 레지스트리를 부르면 pdfminer 의존성이 강제된다 — 모듈 docstring 참고)."""
    if not file_path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없음: {file_path}")

    ext = file_path.suffix.lower().lstrip(".")
    if ext in _TEXT_PARSERS:
        doc = _TEXT_PARSERS[ext].parse(file_path.read_text(encoding="utf-8"))
    elif ext in _BINARY_PARSERS:
        doc = _BINARY_PARSERS[ext].parse_bytes(file_path.read_bytes())
    else:
        raise ValueError(f"지원하지 않는 형식: {ext or file_path.name}")

    doc.metadata["source"] = str(file_path)
    doc.metadata["format"] = ext
    return doc


def _split_by_h1(blocks: list[Block]) -> list[tuple[str | None, list[Block]]]:
    """HEADING(level==1) 경계로 분리한다.

    h1 블록 자체는 다음 그룹의 제목으로 소비되고 본문에는 남기지 않는다(h1 텍스트를
    "챕터 제목"으로 쓰라는 요구사항을 그대로 반영 — 본문에 같은 제목을 중복 표시하지
    않는다). 첫 h1 이전에 내용이 있으면(전문 없이 바로 본문이 시작하는 원고) 그 내용은
    제목 없는 선행 그룹이 되어 파일명 스템 제목을 받는다(import_manuscript 에서 처리).
    블록이 하나도 없거나(빈 파일) h1 이 전혀 없으면 그룹은 정확히 1개다.
    """
    groups: list[tuple[str | None, list[Block]]] = []
    current_title: str | None = None
    current_blocks: list[Block] = []

    for block in blocks:
        if block.type == BlockType.HEADING and block.meta.get("level") == 1:
            if current_blocks or current_title is not None:
                groups.append((current_title, current_blocks))
            current_title = _plain_text(block.content)
            current_blocks = []
            continue
        current_blocks.append(block)

    if current_blocks or current_title is not None or not groups:
        groups.append((current_title, current_blocks))

    return groups


def _plain_text(fragment: str) -> str:
    """HEADING 블록의 content(정본 인라인 프래그먼트 — DOCX 는 strong/em/u 태그를 포함할
    수 있다, docx.py:139-152 `_run_inline`)를 챕터 제목용 평문으로 변환한다.
    태그 제거 + HTML 엔티티 언이스케이프."""
    return unescape(_TAG_RE.sub("", fragment)).strip()
