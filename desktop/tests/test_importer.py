"""desktop/importer.py(원고 가져오기 P1 슬라이스3) 단위 테스트.

TXT/MD 는 합성 콘텐츠(제어 용이)로 h1 분리·래퍼·빈파일 엣지를 검증한다. DOCX/HWP/HWPX
는 backend/tests/engine/doc/reference_data 에서 복사해온 실제 파일
(desktop/tests/fixtures/sample.*)로 "실제로 파싱이 성공하는가"를 검증한다 — 이 세
포맷은 backend 엔진에서 HEADING 블록을 아예 못 내거나(HWP/HWPX) 픽스처 자체에 h1
스타일이 있다는 보장이 없어(DOCX) h1 분리 자체는 TXT/MD 로만 검증한다.
"""

from pathlib import Path

import pytest

from importer import import_manuscript

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def _write(tmp_path, name, content):
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


class TestTxt:
    def test_no_headings_single_chapter_titled_by_filename_stem(self, tmp_path):
        path = _write(tmp_path, "hello world.txt", "첫 문단입니다.\n\n둘째 문단입니다.")
        chapters = import_manuscript(path)

        assert len(chapters) == 1
        assert chapters[0]["title"] == "hello world"
        assert chapters[0]["html"].startswith('<article data-juldoc="1">')
        assert chapters[0]["html"].endswith("</article>")
        assert "첫 문단입니다" in chapters[0]["html"]
        assert "둘째 문단입니다" in chapters[0]["html"]

    def test_empty_file_yields_one_chapter_with_empty_wrapper(self, tmp_path):
        path = tmp_path / "empty.txt"
        path.write_text("", encoding="utf-8")
        chapters = import_manuscript(path)

        assert len(chapters) == 1
        assert chapters[0]["title"] == "empty"
        assert chapters[0]["html"] == '<article data-juldoc="1"></article>'


class TestMarkdownH1Split:
    def test_two_h1_sections_split_into_two_chapters(self, tmp_path):
        path = _write(
            tmp_path,
            "manuscript.md",
            "# 1장 시작\n\n첫 장 본문.\n\n## 소제목\n\n소제목 본문.\n\n"
            "# 2장 다음\n\n둘째 장 본문.\n",
        )
        chapters = import_manuscript(path)

        assert len(chapters) == 2
        assert chapters[0]["title"] == "1장 시작"
        assert chapters[1]["title"] == "2장 다음"
        # h2 는 챕터를 나누지 않고 첫 챕터 본문에 남는다.
        assert "소제목 본문" in chapters[0]["html"]
        assert "둘째 장 본문" in chapters[1]["html"]
        # h1 자체는 제목으로 소비되고 본문에는 중복되지 않는다.
        assert "1장 시작" not in chapters[0]["html"]
        assert "2장 다음" not in chapters[1]["html"]

    def test_no_h1_falls_back_to_filename_stem_single_chapter(self, tmp_path):
        path = _write(tmp_path, "noh1.md", "## 소제목만\n\n본문.\n")
        chapters = import_manuscript(path)

        assert len(chapters) == 1
        assert chapters[0]["title"] == "noh1"
        assert "본문" in chapters[0]["html"]

    def test_content_before_first_h1_becomes_leading_untitled_chapter(self, tmp_path):
        path = _write(
            tmp_path, "preamble.md", "전문입니다.\n\n# 진짜 1장\n\n본문.\n"
        )
        chapters = import_manuscript(path)

        assert len(chapters) == 2
        assert chapters[0]["title"] == "preamble"
        assert "전문입니다" in chapters[0]["html"]
        assert chapters[1]["title"] == "진짜 1장"
        assert "본문" in chapters[1]["html"]

    def test_h1_with_no_trailing_content_still_becomes_its_own_chapter(self, tmp_path):
        path = _write(tmp_path, "solo.md", "# 단독 제목\n")
        chapters = import_manuscript(path)

        assert len(chapters) == 1
        assert chapters[0]["title"] == "단독 제목"
        assert chapters[0]["html"] == '<article data-juldoc="1"></article>'

    def test_every_chapter_html_keeps_article_wrapper(self, tmp_path):
        path = _write(
            tmp_path,
            "wrapped.md",
            "# A\n\n본문A\n\n# B\n\n본문B\n",
        )
        for chapter in import_manuscript(path):
            assert chapter["html"].startswith('<article data-juldoc="1">')
            assert chapter["html"].endswith("</article>")


@pytest.mark.parametrize(
    "fixture_name",
    ["sample.docx", "sample.hwp", "sample.hwpx"],
)
def test_real_fixture_parses_successfully(fixture_name):
    """실 DOCX/HWP/HWPX 파일이 backend 파서를 통해 실제로 파싱되는지 확인(실측 근거).

    ⚠️ fixtures/ 는 backend reference_data(실제 개인문서 포함 — gitignore 대상, 로컬 전용)
    복사본이라 **커밋 금지**(desktop/.gitignore 처리). backend 테스트와 동일하게
    파일 부재 환경(CI·새 클론)에선 skip. h1 분리 자체는 합성 MD로 검증한다.
    """
    fixture_path = FIXTURES_DIR / fixture_name
    if not fixture_path.exists():
        pytest.skip(f"local-only fixture 없음: {fixture_path}")

    chapters = import_manuscript(fixture_path)

    assert len(chapters) >= 1
    total_len = sum(len(c["html"]) for c in chapters)
    assert total_len > 100, "파싱 결과가 지나치게 짧다 — 본문이 비어있을 가능성"
    for chapter in chapters:
        assert chapter["html"].startswith('<article data-juldoc="1">')
        assert chapter["html"].endswith("</article>")
        assert chapter["title"]  # 빈 문자열이 아님


def test_unsupported_extension_raises_value_error(tmp_path):
    path = _write(tmp_path, "unsupported.pdf", "not really a pdf")
    with pytest.raises(ValueError):
        import_manuscript(path)


def test_missing_file_raises_file_not_found_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        import_manuscript(tmp_path / "does-not-exist.txt")
