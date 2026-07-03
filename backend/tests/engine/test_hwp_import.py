"""hwp_to_neutral_blocks 단위 테스트.

두 층위로 검증한다:
1. IR→블록 변환 로직 — mock IR pydantic 객체(ParagraphBlock/InlineRun/TableBlock/...)를
   코드로 직접 구성해 순회·변환을 검증(파싱 자체와 분리).
2. 실 파싱 — 손수 만든 최소 HWPX 바이너리를 rhwp 로 실제 파싱해 end-to-end 검증.
"""
import pytest
from rhwp.ir import nodes

from src.engine.imports.hwp_import import (
    InvalidHwpFile,
    hwp_to_neutral_blocks,
)
from tests.fixtures.hwpx_fixture import build_hwpx, build_hwpx_marked

_PROV = nodes.Provenance(section_idx=0, para_idx=0)


def _doc(*blocks):
    return nodes.HwpDocument(body=list(blocks))


def _run(text, **kw):
    return nodes.InlineRun(text=text, **kw)


def _para(inlines=(), text=""):
    return nodes.ParagraphBlock(text=text, inlines=list(inlines), prov=_PROV)


# ── 1. IR→블록 변환 로직 (mock IR 객체) ──────────────────────────────────


def test_paragraph_marks_bold_and_italic():
    doc = _doc(_para([
        _run("보통"),
        _run("굵게", bold=True),
        _run("기울임", italic=True),
        _run("둘다", bold=True, italic=True),
    ]))
    # from_ir 로직만 태우려고 monkeypatch 대신 내부 순회를 직접 테스트하기 위해
    # hwp_to_neutral_blocks 는 파싱을 하므로, 여기서는 변환 함수 경로를 재현한다.
    from src.engine.imports.hwp_import import _emit
    out = []
    for b in doc.body:
        _emit(b, out)
    assert out == [{
        "type": "p",
        "spans": [
            {"text": "보통", "marks": []},
            {"text": "굵게", "marks": ["strong"]},
            {"text": "기울임", "marks": ["em"]},
            {"text": "둘다", "marks": ["strong", "em"]},  # MARKS 순서: strong→em
        ],
    }]


def test_empty_paragraph_dropped():
    from src.engine.imports.hwp_import import _emit
    out = []
    _emit(_para([_run("")], text=""), out)  # 빈 텍스트 런 + 빈 text
    _emit(_para([], text="   "), out)  # 공백뿐 → 폴백도 버림
    assert out == []


def test_paragraph_text_fallback_when_no_inlines():
    from src.engine.imports.hwp_import import _emit
    out = []
    _emit(_para([], text="인라인없음"), out)
    assert out == [{"type": "p", "spans": [{"text": "인라인없음", "marks": []}]}]


def test_list_item_becomes_plain_paragraph():
    li = nodes.ListItemBlock(text="목록항목", inlines=[_run("목록항목")], prov=_PROV)
    from src.engine.imports.hwp_import import _emit
    out = []
    _emit(li, out)
    assert out == [{"type": "p", "spans": [{"text": "목록항목", "marks": []}]}]


def test_table_row_per_paragraph_cells_joined_by_two_spaces():
    def cell(row, col, text):
        return nodes.TableCell(
            row=row, col=col, grid_index=row * 2 + col,
            blocks=[_para([_run(text)], text=text)],
        )
    table = nodes.TableBlock(
        rows=2, cols=2, prov=_PROV,
        cells=[cell(0, 0, "A"), cell(0, 1, "B"), cell(1, 0, "C"), cell(1, 1, "D")],
    )
    from src.engine.imports.hwp_import import _emit
    out = []
    _emit(table, out)
    assert out == [
        {"type": "p", "spans": [{"text": "A  B", "marks": []}]},
        {"type": "p", "spans": [{"text": "C  D", "marks": []}]},
    ]


def test_unknown_block_extracts_text_not_dropped():
    # FormulaBlock 은 paragraph/table/list_item 이 아님 → 대체텍스트만 문단으로
    formula = nodes.FormulaBlock(script="x^2 + y", text_alt="x^2 + y", prov=_PROV)
    from src.engine.imports.hwp_import import _emit
    out = []
    _emit(formula, out)
    assert out == [{"type": "p", "spans": [{"text": "x^2 + y", "marks": []}]}]


# ── 2. 실 파싱 (손수 만든 최소 HWPX) ─────────────────────────────────────


def test_real_hwpx_parses_to_paragraphs():
    data = build_hwpx(["첫 번째 문단입니다", "두 번째 문단입니다"])
    blocks = hwp_to_neutral_blocks(data)
    assert blocks == [
        {"type": "p", "spans": [{"text": "첫 번째 문단입니다", "marks": []}]},
        {"type": "p", "spans": [{"text": "두 번째 문단입니다", "marks": []}]},
    ]


def test_real_hwpx_marks_propagate():
    blocks = hwp_to_neutral_blocks(build_hwpx_marked())
    assert len(blocks) == 1
    spans = blocks[0]["spans"]
    texts = {s["text"]: s["marks"] for s in spans}
    assert texts["굵게"] == ["strong"]
    assert texts["기울임"] == ["em"]
    assert texts["보통"] == []


@pytest.mark.parametrize("data", [b"", b"not an hwp file at all", b"PK\x03\x04garbage"])
def test_invalid_bytes_raise_domain_error(data):
    with pytest.raises(InvalidHwpFile) as ei:
        hwp_to_neutral_blocks(data)
    assert ei.value.status_code == 422  # ValidationError 상속 → 표현층 422
