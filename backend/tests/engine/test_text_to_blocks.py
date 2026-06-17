"""순수 변환기 단위 테스트 — 기능: '원고 업로드 → 정본 HTML 변환' (dc-f8acfa26)."""
from src.engine.imports.text_to_blocks import text_to_blocks


def test_empty_returns_no_blocks():
    assert text_to_blocks("") == []
    assert text_to_blocks("\n\n  \n") == []


def test_single_paragraph():
    blocks = text_to_blocks("첫 문장입니다.")
    assert blocks == [{"type": "P", "html": "<p>첫 문장입니다.</p>"}]


def test_blank_line_separates_paragraphs():
    blocks = text_to_blocks("문단 하나.\n\n문단 둘.")
    assert [b["type"] for b in blocks] == ["P", "P"]
    assert blocks[0]["html"] == "<p>문단 하나.</p>"
    assert blocks[1]["html"] == "<p>문단 둘.</p>"


def test_consecutive_lines_join_into_one_paragraph():
    blocks = text_to_blocks("한 줄\n이어지는 줄")
    assert blocks == [{"type": "P", "html": "<p>한 줄 이어지는 줄</p>"}]


def test_headings():
    blocks = text_to_blocks("# 제목\n## 부제\n### 소제목")
    assert blocks == [
        {"type": "H1", "html": "<h1>제목</h1>"},
        {"type": "H2", "html": "<h2>부제</h2>"},
        {"type": "H3", "html": "<h3>소제목</h3>"},
    ]


def test_blockquote():
    blocks = text_to_blocks("> 인용문")
    assert blocks == [{"type": "QUOTE", "html": "<blockquote>인용문</blockquote>"}]


def test_horizontal_rule():
    for token in ("---", "***", "___"):
        assert text_to_blocks(token) == [{"type": "HR", "html": "<hr/>"}]


def test_html_is_escaped():
    blocks = text_to_blocks("a < b & c > d")
    assert blocks[0]["html"] == "<p>a &lt; b &amp; c &gt; d</p>"


def test_mixed_document_structure_and_order():
    raw = "# 한줄\n\n베스트셀러인데 왜 작가는 돈을 못 벌까.\n\n> 명언\n\n---\n\n다음 문단."
    blocks = text_to_blocks(raw)
    assert [b["type"] for b in blocks] == ["H1", "P", "QUOTE", "HR", "P"]


def test_crlf_normalized():
    assert text_to_blocks("줄1\r\n\r\n줄2") == [
        {"type": "P", "html": "<p>줄1</p>"},
        {"type": "P", "html": "<p>줄2</p>"},
    ]
