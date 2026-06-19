"""EPUB 3 생성 엔진 테스트 (zip 구조·OPF·spine·내용)."""
import io
import zipfile

from src.engine.publishing.epub import EpubBook, EpubChapter, build_epub

MODIFIED = "2026-06-19T12:00:00Z"


def _book():
    return EpubBook(
        title="한 줄",
        language="ko",
        identifier="urn:uuid:abc",
        author="박작가",
        chapters=[
            EpubChapter(title="프롤로그", html="<h1>제목</h1><p>본문입니다.</p>"),
            EpubChapter(title="1장", html="<p>둘째 장.</p>"),
        ],
    )


def _zip(data):
    return zipfile.ZipFile(io.BytesIO(data))


def test_mimetype_first_and_stored():
    z = _zip(build_epub(_book(), MODIFIED))
    assert z.namelist()[0] == "mimetype"  # 반드시 첫 엔트리
    assert z.read("mimetype") == b"application/epub+zip"
    assert z.getinfo("mimetype").compress_type == zipfile.ZIP_STORED  # 비압축


def test_required_files_present():
    z = _zip(build_epub(_book(), MODIFIED))
    names = z.namelist()
    for f in [
        "META-INF/container.xml",
        "OEBPS/package.opf",
        "OEBPS/nav.xhtml",
        "OEBPS/chap_0.xhtml",
        "OEBPS/chap_1.xhtml",
    ]:
        assert f in names


def test_opf_metadata_and_spine_order():
    opf = _zip(build_epub(_book(), MODIFIED)).read("OEBPS/package.opf").decode()
    assert "<dc:title>한 줄</dc:title>" in opf
    assert "urn:uuid:abc" in opf
    assert "<dc:language>ko</dc:language>" in opf
    assert "박작가" in opf
    assert "<dc:publisher>한줄</dc:publisher>" in opf
    assert "dcterms:modified" in opf
    assert opf.index('idref="chap0"') < opf.index('idref="chap1"')  # 순서 보존


def test_chapter_content_and_nav():
    z = _zip(build_epub(_book(), MODIFIED))
    c0 = z.read("OEBPS/chap_0.xhtml").decode()
    assert "<h1>제목</h1>" in c0 and "<p>본문입니다.</p>" in c0
    nav = z.read("OEBPS/nav.xhtml").decode()
    assert "프롤로그" in nav and "1장" in nav


def test_empty_book_still_valid_zip():
    z = _zip(build_epub(EpubBook(title="빈책", language="ko", identifier="urn:uuid:x"), MODIFIED))
    assert "OEBPS/package.opf" in z.namelist()
    assert z.namelist()[0] == "mimetype"
