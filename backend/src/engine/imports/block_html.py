"""정본 블록 HTML 검증 (순수 함수, stdlib만) — 신뢰 못 하는 클라이언트가 보낸
`{type, html}` 블록의 html 이 우리가 생성/소비하는 통제된 HTML 부분집합인지 확인한다.

문법의 정본은 서버의 `text_to_blocks.py`(원고 → 블록 생성)와 프론트
`web/src/writer/core/serialize.js`(에디터 직렬화)다. 둘 다 오직
`<p|h1|h2|h3|blockquote>` 외곽 + 내부 순수텍스트/`<strong>`/`<em>`(중첩 허용, 무속성)
+ `<hr/>` 만 만든다. 여기서 그와 100% 동일한 문법만 통과시켜, 로그인 사용자가 API 를
직접 호출해 임의 HTML(`<script>`·속성 인젝션 등)을 저장·EPUB 삽입·서점 배포로
흘려보내는 것을 막는다.
"""
from html.parser import HTMLParser

# 블록 타입 → 허용 외곽 태그 (HR 은 별도 분기: html 이 정확히 "<hr/>" 여야 함)
_ALLOWED_OUTER = {"P": "p", "H1": "h1", "H2": "h2", "H3": "h3", "QUOTE": "blockquote"}
_ALLOWED_INNER = {"strong", "em"}


class InvalidBlockHtml(ValueError):
    """블록 html 이 정본 문법을 벗어남."""


class _BlockHtmlValidator(HTMLParser):
    """태그 스택을 추적하며 정본 문법 위반 시 즉시 InvalidBlockHtml 을 던진다."""

    def __init__(self, outer_tag: str):
        super().__init__(convert_charrefs=True)
        self._outer = outer_tag
        self._stack: list[str] = []
        self._opened_top = False

    def _fail(self, reason: str) -> None:
        raise InvalidBlockHtml(reason)

    def handle_starttag(self, tag, attrs):
        if attrs:  # (b) 속성 일절 불가
            self._fail(f"태그 <{tag}> 에 속성 불가")
        if not self._stack:  # depth 0 = 최상위
            if self._opened_top:  # (e) 최상위에 형제 요소
                self._fail("최상위에 형제 요소 불가")
            if tag != self._outer:  # (e) 외곽 태그가 블록 타입과 불일치
                self._fail(f"외곽 태그 <{tag}> != <{self._outer}>")
            self._opened_top = True
        elif tag not in _ALLOWED_INNER:  # (a) 내부는 strong/em 만
            self._fail(f"허용 안 된 태그 <{tag}>")
        self._stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        # 정본 내부엔 자기종결 태그(<x/>)가 없다 (HR 은 문자열 완전일치로 이미 처리).
        self._fail(f"자기종결 태그 <{tag}/> 불가")

    def handle_endtag(self, tag):
        if not self._stack or self._stack[-1] != tag:  # (d) 불균형/미종료
            self._fail(f"태그 불균형: </{tag}>")
        self._stack.pop()

    def handle_data(self, data):
        if not self._stack:  # (c) 최상위 텍스트(=바깥으로 샌 텍스트/leading·trailing 공백)
            self._fail("최상위 텍스트 불가")

    def handle_comment(self, data):
        self._fail("주석 불가")

    def handle_decl(self, decl):
        self._fail("선언 불가")

    def handle_pi(self, data):
        self._fail("처리 명령 불가")

    def finish(self) -> None:
        if self._stack:  # (d) 닫히지 않은 태그
            self._fail("닫히지 않은 태그")
        if not self._opened_top:  # 외곽 태그가 아예 없음(빈 문자열/텍스트뿐)
            self._fail("외곽 태그 없음")


def validate_block_html(block_type: str, html: str) -> None:
    """블록 html 이 정본 문법(text_to_blocks.py/serialize.js 와 동일)을 만족하는지 검증.

    위반 시 InvalidBlockHtml 을 던진다. 반환값 없음(통과=조용히 리턴).
    """
    if block_type == "HR":
        if html != "<hr/>":
            raise InvalidBlockHtml(f"HR html 은 '<hr/>' 여야 함: {html!r}")
        return
    outer = _ALLOWED_OUTER.get(block_type)
    if outer is None:
        raise InvalidBlockHtml(f"알 수 없는 블록 타입: {block_type!r}")
    parser = _BlockHtmlValidator(outer)
    parser.feed(html)
    parser.close()
    parser.finish()
