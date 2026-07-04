"""PDF 원고 → 중립 doc 블록 변환 (상태 없는 순수 파서).

프론트 DOCX/EPUB 가져오기와 완전히 같은 중립 형식을 낸다:
    {"blocks": [{"type": "p"|"h1"|"h2"|"h3",
                 "spans": [{"text": str, "marks": ["strong"|"em"]}]}]}
그래서 프론트 neutralToPmDoc 로 그대로 에디터에 적재된다.

판정 알고리즘 (실측 튜닝, 테스트로 검증):
- baseline: 문서 전체 span 을 글자수 가중으로 집계한 최빈 폰트크기(=본문 크기).
- 헤딩: block 대표크기 / baseline 비율이 1.5↑ h1, 1.25↑ h2, 1.15↑ h3, 그 미만 p.
- 문단: PyMuPDF get_text("dict") 의 block 하나를 문단 하나로(안의 여러 line 이어붙임).
- 서식: span flags 로 bold(16)·italic(2) → marks(["strong","em"]).

pymupdf(fitz)는 지연 임포트(함수 내부) — 외부 파일파싱 의존성 컨벤션. 임포트 실패는
RuntimeError(엔드포인트가 503), 파일 자체 파싱 실패는 InvalidPdfFile(422)로 가른다.
※ fitz.FileDataError 는 RuntimeError 하위라, 파싱 구간은 반드시 InvalidPdfFile 로 감싼다.
"""
from collections import Counter

from src.shared.errors import InvalidPdfFile

# 폰트 플래그 비트 (실측: hebo/heit 로 확인)
_FLAG_BOLD = 1 << 4  # 16
_FLAG_ITALIC = 1 << 1  # 2

# baseline 대비 헤딩 임계 비율 (큰 순으로 판정)
_H1_RATIO = 1.5
_H2_RATIO = 1.25
_H3_RATIO = 1.15


def _marks_for(flags: int) -> list[str]:
    """span flags → marks. 순서는 MARKS(['strong','em'])와 동일하게 결정적."""
    marks = []
    if flags & _FLAG_BOLD:
        marks.append("strong")
    if flags & _FLAG_ITALIC:
        marks.append("em")
    return marks


def _round_size(size: float) -> float:
    """폰트 크기 float 노이즈 제거 — 0.1pt 로 반올림해 최빈값 집계."""
    return round(size, 1)


def _baseline_size(blocks: list) -> float:
    """문서 전체 span 을 글자수 가중으로 집계 → 최빈 크기(본문 크기)."""
    weight: Counter = Counter()
    for block in blocks:
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "")
                n = len(text.strip())
                if n:
                    weight[_round_size(span.get("size", 0.0))] += n
    if not weight:
        return 0.0
    # 가장 큰 가중치, 동률이면 더 작은 크기(본문일 확률↑)
    top = max(weight.values())
    return min(s for s, w in weight.items() if w == top)


def _block_repr_size(block: dict) -> float:
    """block 대표 크기 — 글자수 가중 최빈(제목 한 줄 판정용). 동률이면 더 큰 크기."""
    weight: Counter = Counter()
    for line in block.get("lines", []):
        for span in line.get("spans", []):
            text = span.get("text", "")
            n = len(text.strip())
            if n:
                weight[_round_size(span.get("size", 0.0))] += n
    if not weight:
        return 0.0
    top = max(weight.values())
    return max(s for s, w in weight.items() if w == top)


def _block_type(repr_size: float, baseline: float) -> str:
    if baseline <= 0:
        return "p"
    ratio = repr_size / baseline
    if ratio >= _H1_RATIO:
        return "h1"
    if ratio >= _H2_RATIO:
        return "h2"
    if ratio >= _H3_RATIO:
        return "h3"
    return "p"


def _block_spans(block: dict) -> list[dict]:
    """block 안의 모든 line·span 을 이어붙여 하나의 spans 배열로.

    - 줄바꿈은 공백으로(단어 붙음 방지).
    - 같은 marks 인접 span 은 병합(본문이 잘게 쪼개지지 않게).
    - 빈 텍스트 span 은 버림.
    """
    raw: list[dict] = []
    lines = block.get("lines", [])
    for i, line in enumerate(lines):
        for span in line.get("spans", []):
            text = span.get("text", "")
            if text:
                raw.append({"text": text, "marks": _marks_for(span.get("flags", 0))})
        # 줄 사이 공백 (마지막 줄 뒤엔 안 붙임)
        if i < len(lines) - 1 and raw:
            raw.append({"text": " ", "marks": []})

    # 인접 동일 marks 병합
    merged: list[dict] = []
    for span in raw:
        if merged and merged[-1]["marks"] == span["marks"]:
            merged[-1]["text"] += span["text"]
        else:
            merged.append(dict(span))

    # 양끝 공백 정리 + 빈 span 제거
    if merged:
        merged[0]["text"] = merged[0]["text"].lstrip()
        merged[-1]["text"] = merged[-1]["text"].rstrip()
    return [s for s in merged if s["text"]]


def pdf_to_neutral_blocks(data: bytes) -> list[dict]:
    """PDF 바이트 → 중립 doc 블록 리스트.

    반환: [{"type": "p"|"h1"|"h2"|"h3", "spans": [{"text","marks"}]}]
    """
    try:
        import fitz  # 지연 임포트 (pymupdf) — 미설치/로드실패 → 503 로 잡히게 RuntimeError
    except ImportError as e:
        raise RuntimeError("pymupdf(fitz) is not available") from e

    try:
        doc = fitz.open(stream=data, filetype="pdf")
        page_dicts = [page.get_text("dict") for page in doc]
    except RuntimeError as e:
        # fitz.FileDataError 등 파일 파싱 실패 (RuntimeError 하위) → 손상 파일
        raise InvalidPdfFile() from e
    except Exception as e:  # noqa: BLE001 — 알 수 없는 파싱 오류도 사용자 친화 422 로
        raise InvalidPdfFile() from e

    all_blocks = [b for pd in page_dicts for b in pd.get("blocks", [])]
    baseline = _baseline_size(all_blocks)

    result: list[dict] = []
    for block in all_blocks:
        if not block.get("lines"):
            continue  # 이미지 블록 등 (텍스트 없음)
        spans = _block_spans(block)
        if not spans:
            continue  # 공백만 있는 블록은 버림
        btype = _block_type(_block_repr_size(block), baseline)
        result.append({"type": btype, "spans": spans})
    return result
