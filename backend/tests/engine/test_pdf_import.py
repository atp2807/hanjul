"""pdf_to_neutral_blocks 단위테스트 — 실제 pymupdf 로 유효 PDF 를 만들어 진짜 파싱 검증.

CI(Ubuntu) 의존성 없게 픽스처는 영문/숫자만 (텍스트 추출은 언어 무관 — 한글도 동일 경로).
폰트: helv(보통)·hebo(굵게)·heit(기울임). 크기로 헤딩 판정.
"""
import fitz
import pytest
from src.engine.imports.pdf_import import pdf_to_neutral_blocks
from src.shared.errors import InvalidPdfFile


def build_pdf(paragraphs_with_style) -> bytes:
    """[(text, fontsize, fontname), ...] → PDF bytes. y 간격을 크게 벌려 문단 분리 보장."""
    doc = fitz.open()
    page = doc.new_page()
    y = 72
    for text, size, fontname in paragraphs_with_style:
        page.insert_text((72, y), text, fontsize=size, fontname=fontname)
        y += size * 3  # 넉넉히 벌려 서로 다른 block 으로
    return doc.tobytes()


def test_heading_by_font_size():
    data = build_pdf([
        ("Big Title", 24, "helv"),   # 24/11 = 2.18 → h1
        ("Section Head", 15, "helv"),  # 15/11 = 1.36 → h2
        ("Body paragraph text here", 11, "helv"),  # baseline
        ("Another body line of prose", 11, "helv"),
    ])
    blocks = pdf_to_neutral_blocks(data)
    by_text = {b["spans"][0]["text"]: b for b in blocks}
    assert by_text["Big Title"]["type"] == "h1"
    assert by_text["Section Head"]["type"] == "h2"
    assert by_text["Body paragraph text here"]["type"] == "p"
    assert by_text["Another body line of prose"]["type"] == "p"


def test_bold_and_italic_marks():
    data = build_pdf([
        ("bold line here now", 11, "hebo"),   # 굵게
        ("italic line here now", 11, "heit"),  # 기울임
        ("plain body line one", 11, "helv"),
        ("plain body line two", 11, "helv"),
    ])
    blocks = pdf_to_neutral_blocks(data)
    by_text = {b["spans"][0]["text"]: b for b in blocks}
    assert by_text["bold line here now"]["spans"][0]["marks"] == ["strong"]
    assert by_text["italic line here now"]["spans"][0]["marks"] == ["em"]
    assert by_text["plain body line one"]["spans"][0]["marks"] == []


def test_mixed_marks_within_paragraph():
    """한 줄 안에서 bold/italic 이 섞이면 span 단위로 marks 가 갈린다."""
    doc = fitz.open()
    page = doc.new_page()
    # 같은 y·같은 line 에 이어 그려서 한 문단(한 line) 안 여러 span 구성
    x = 72
    for text, fn in [("normal ", "helv"), ("bold", "hebo"), (" tail", "helv")]:
        page.insert_text((x, 100), text, fontsize=11, fontname=fn)
        x += fitz.get_text_length(text, fontname=fn, fontsize=11)
    # baseline 확보용 본문 두 줄
    page.insert_text((72, 160), "filler body prose line", fontsize=11, fontname="helv")
    page.insert_text((72, 200), "another filler prose line", fontsize=11, fontname="helv")
    blocks = pdf_to_neutral_blocks(doc.tobytes())

    mixed = next(b for b in blocks if b["spans"][0]["text"].startswith("normal"))
    assert mixed["type"] == "p"
    texts_marks = [(s["text"], s["marks"]) for s in mixed["spans"]]
    assert ("bold", ["strong"]) in texts_marks
    # normal 부분은 marks 없음
    assert any(t.strip() == "normal" and m == [] for t, m in texts_marks) or texts_marks[0][1] == []


def test_blank_only_dropped():
    data = build_pdf([
        ("   ", 11, "helv"),      # 공백만 → 버림
        ("real content here now", 11, "helv"),
        ("more real content now", 11, "helv"),
    ])
    blocks = pdf_to_neutral_blocks(data)
    texts = [b["spans"][0]["text"] for b in blocks]
    assert "real content here now" in texts
    assert not any(t.strip() == "" for t in texts)


def test_corrupt_bytes_raise_invalid_pdf():
    with pytest.raises(InvalidPdfFile):
        pdf_to_neutral_blocks(b"not a pdf")
