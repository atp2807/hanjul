"""정본 블록 HTML 검증기 단위 테스트 — 신뢰 못 하는 클라이언트 html 방어.

정본 문법(text_to_blocks.py/serialize.js 와 동일)만 통과해야 한다.
"""
import pytest

from src.engine.imports.block_html import InvalidBlockHtml, validate_block_html


@pytest.mark.parametrize(
    "block_type,html",
    [
        ("P", "<p>순수 텍스트입니다.</p>"),
        ("H1", "<h1>제목</h1>"),
        ("H2", "<h2>부제</h2>"),
        ("H3", "<h3>소제목</h3>"),
        ("QUOTE", "<blockquote>인용문</blockquote>"),
        ("HR", "<hr/>"),
        ("P", "<p><strong>굵게</strong></p>"),
        ("P", "<p><em>기울임</em></p>"),
        ("P", "<p>앞 <strong>굵게</strong> 뒤 <em>기울임</em>.</p>"),
        ("P", "<p><strong><em>굵고 기울임</em></strong></p>"),  # 중첩
        ("P", "<p>이스케이프된 a &lt; b &amp; c &gt; d</p>"),  # 엔티티는 텍스트로 디코드
        ("P", "<p></p>"),  # 빈 내용 허용(serialize 가 만들 수 있음)
    ],
)
def test_valid_passes(block_type, html):
    validate_block_html(block_type, html)  # 예외 없어야 함


@pytest.mark.parametrize(
    "block_type,html,why",
    [
        ("P", "<p><script>alert(1)</script></p>", "script 태그"),
        ("P", '<p onclick="x">y</p>', "속성 있음"),
        ("P", "<div>내용</div>", "허용 안 된 외곽 태그"),
        ("P", "<p>안 닫힘", "미종료 태그"),
        ("P", "앞으로 샌 텍스트 <p>x</p>", "최상위 텍스트 누출"),
        ("P", " <p>x</p>", "leading 공백"),
        ("P", "<p>x</p> ", "trailing 공백"),
        ("P", "<p>a</p><p>b</p>", "최상위 형제 요소"),
        ("HR", "<hr>", "HR 인데 <hr/> 아님"),
        ("HR", "<hr />", "HR 인데 <hr/> 아님(공백)"),
        ("P", "<h1>제목</h1>", "block_type 과 외곽 태그 불일치"),
        ("P", "<p><strong>안 닫힘</p>", "내부 태그 불균형"),
        ("P", '<p><a href="http://x">링크</a></p>', "허용 안 된 내부 태그"),
        ("P", "", "빈 문자열(외곽 없음)"),
        ("WHAT", "<p>x</p>", "알 수 없는 블록 타입"),
    ],
)
def test_invalid_raises(block_type, html, why):
    with pytest.raises(InvalidBlockHtml):
        validate_block_html(block_type, html)
