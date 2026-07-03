"""HWP/HWPX 원고 → 중립 블록 변환 (rhwp IR 순회).

한글(HWP5)·한컴(HWPX) 바이너리를 `rhwp` 로 파싱해 IR(`HwpDocument`) 트리를 얻고,
프론트 에디터가 소비하는 중립 doc 블록 리스트로 변환한다. 출력 형식은 프론트
`web/src/writer/adapters/docx_import.js`(DOCX 가져오기)가 만드는 것과 **완전히 동일** —
같은 `neutralToPmDoc` 경로로 에디터에 적재되므로 필드명·구조가 어긋나면 안 된다.

    {"type": "p"|"h1"|"h2"|"h3"|"quote"|"hr", "spans": [{"text": str, "marks": [...]}]}
    # hr 은 spans 없음. marks 는 "strong"(bold)·"em"(italic) 부분집합.

헤딩(제목1/2 등)은 rhwp IR 에 신뢰할 수 있는 필드로 노출되지 않는다 —
`ParagraphBlock.kind` 는 항상 `'paragraph'` 고정이고, 스타일은 `InlineRun.raw_style_id`
(폰트/크기 escape 용 인덱스)뿐이라 헤딩 레벨로 안전히 역매핑할 수 없다. 잘못된 헤딩
추측보다 정직하게 평문단으로 두는 편이 나으므로(조용히 틀리지 않기) **모든 문단은
`type:'p'`** 로 낸다. h1~h3/quote/hr 은 형식 호환을 위해 유지(프론트가 다른 경로에서
쓸 수 있음)하되 여기서는 산출하지 않는다.

`rhwp` 는 지연 임포트한다 — 2026-07-04 확인: `rhwp-python` 0.7.0/0.8.0의
manylinux aarch64 휠이 번들한 libfreetype 에 확장모듈이 요구하는 심볼
(FT_Palette_Select)이 빠져 있어 EC2(aarch64) 환경에서 `import rhwp` 자체가
`ImportError`로 죽는다(업스트림 패키징 결함, macOS/x86_64에선 재현 안 됨).
모듈 최상단에서 임포트하면 이 오류가 앱 기동 자체를 막아 HWP 와 무관한 다른
기능까지 전부 죽는다 — 그래서 실제 호출 시점에만 시도하고, 실패하면
RuntimeError 로 감싸 표현층이 503(그 요청만 실패)으로 매핑하게 한다.
"""
from src.shared.errors import ValidationError

# marks 순서는 프론트 MARKS(web/src/writer/core/blocks.js) 와 동일: strong → em
_MARK_ORDER = ("strong", "em")


class InvalidHwpFile(ValidationError):
    """HWP/HWPX 바이너리가 손상됐거나 지원하지 않는 포맷 — 표현층이 422 로 매핑."""

    default_detail = "HWP 파일을 읽을 수 없어요. 손상되었거나 지원하지 않는 형식이에요."


def _load_rhwp():
    try:
        import rhwp
    except ImportError as e:  # 환경에 따라 네이티브 확장 로드가 실패할 수 있음 → 503
        raise RuntimeError("HWP 파싱 기능을 지금 이 서버에서 쓸 수 없어요.") from e
    return rhwp


def _marks_for(run) -> list[str]:
    """InlineRun 의 서식 → 중립 marks (bold→strong, italic→em, MARKS 순서 보존)."""
    active = {"strong": bool(getattr(run, "bold", False)), "em": bool(getattr(run, "italic", False))}
    return [m for m in _MARK_ORDER if active[m]]


def _spans_from_inlines(inlines) -> list[dict]:
    """InlineRun 리스트 → span 리스트 (빈 텍스트 런은 버림)."""
    spans = []
    for run in inlines or []:
        text = getattr(run, "text", "") or ""
        if text:
            spans.append({"text": text, "marks": _marks_for(run)})
    return spans


def _paragraph_spans(block) -> list[dict]:
    """문단성 블록(paragraph/list_item) → span 리스트.

    inlines 가 서식을 담으므로 우선 사용하고, 비어 있으면 평문 text 로 폴백한다.
    """
    spans = _spans_from_inlines(getattr(block, "inlines", None))
    if not spans:
        text = (getattr(block, "text", "") or "").strip()
        if text:
            spans = [{"text": text, "marks": []}]
    return spans


def _plain_text(block) -> str:
    """임의 블록에서 평문 텍스트를 최선-노력으로 추출 (정보 손실 최소화).

    text → inlines → 중첩 blocks(각주/미주/캡션/셀) → 수식/필드 대체텍스트 순으로 시도.
    """
    text = getattr(block, "text", None)
    if text:
        return text
    inlines = getattr(block, "inlines", None)
    if inlines:
        return "".join(getattr(r, "text", "") or "" for r in inlines)
    nested = getattr(block, "blocks", None)
    if nested:
        parts = [_plain_text(b) for b in nested]
        return " ".join(p for p in parts if p)
    for attr in ("text_alt", "cached_value", "script"):
        val = getattr(block, attr, None)
        if val:
            return str(val)
    return ""


def _cell_text(cell) -> str:
    """표 셀 → 평문 텍스트 (셀 안 문단들을 공백으로 이어 붙임)."""
    parts = [_plain_text(b) for b in getattr(cell, "blocks", None) or []]
    return " ".join(p for p in parts if p).strip()


def _emit_table(table, out: list[dict]) -> None:
    """TableBlock → 행마다 문단 하나(셀은 2칸 공백으로 join) — docx_import.js 와 동일."""
    cells = getattr(table, "cells", None) or []
    rows: dict[int, list] = {}
    for cell in cells:
        rows.setdefault(getattr(cell, "row", 0), []).append(cell)
    emitted = False
    for row_idx in sorted(rows):
        texts = [_cell_text(c) for c in sorted(rows[row_idx], key=lambda c: getattr(c, "col", 0))]
        texts = [t for t in texts if t]
        if texts:
            out.append({"type": "p", "spans": [{"text": "  ".join(texts), "marks": []}]})
            emitted = True
    if not emitted:
        # 셀 구조가 비었지만 평문 표 텍스트가 있으면 통째로 한 문단(정보 손실 방지)
        text = (getattr(table, "text", "") or "").strip()
        if text:
            out.append({"type": "p", "spans": [{"text": text, "marks": []}]})


def _emit(node, out: list[dict]) -> None:
    """IR 블록 하나를 중립 블록으로 변환해 out 에 추가 (빈 문단은 버림)."""
    kind = getattr(node, "kind", None)
    if kind == "table":
        _emit_table(node, out)
        return
    if kind in ("paragraph", "list_item"):
        spans = _paragraph_spans(node)
        if spans:
            out.append({"type": "p", "spans": spans})
        return
    # 그 외(picture/formula/footnote/field/unknown 등) — 텍스트만 뽑아 문단으로
    text = _plain_text(node).strip()
    if text:
        out.append({"type": "p", "spans": [{"text": text, "marks": []}]})


def hwp_to_neutral_blocks(data: bytes) -> list[dict]:
    """HWP/HWPX 바이너리 → 중립 블록 리스트.

    Raises:
        InvalidHwpFile: 손상/미지원 포맷(rhwp 가 ValueError 를 던질 때) — 422 로 매핑.
        RuntimeError: rhwp 임포트 자체가 실패(환경 문제) — 표현층이 503 으로 매핑.
    """
    rhwp = _load_rhwp()
    try:
        doc = rhwp.Document.from_bytes(data).to_ir()
    except ValueError as e:  # rhwp: 잘못된 포맷 → 도메인 예외로 감싸 표현층 422
        raise InvalidHwpFile() from e
    blocks: list[dict] = []
    for node in doc.body:
        _emit(node, blocks)
    return blocks
