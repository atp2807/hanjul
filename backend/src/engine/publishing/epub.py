"""EPUB 3 생성 (순수, stdlib만). 정본 HTML 블록 → 유효한 .epub zip.

서점 유통·다운로드의 기본 산출물. 시각(modified)은 외부에서 주입 → 순수/결정론.
"""
import html as _html
import io
import zipfile
from dataclasses import dataclass, field

PUBLISHER = "한줄"


@dataclass
class EpubChapter:
    title: str | None
    html: str  # 그 장의 블록 HTML을 이어붙인 것


@dataclass
class EpubBook:
    title: str
    language: str
    identifier: str          # ISBN 또는 urn:uuid:...
    author: str | None = None
    chapters: list[EpubChapter] = field(default_factory=list)


_CONTAINER = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/package.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>"""

_CSS = """body{font-family:serif;line-height:1.7;margin:1em;}
h1,h2,h3{line-height:1.3;}
blockquote{color:#555;border-left:3px solid #ccc;padding-left:1em;margin-left:0;}"""


def _esc(s: str | None) -> str:
    return _html.escape(s or "", quote=True)


def _chapter_xhtml(ch: EpubChapter, lang: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<!DOCTYPE html>\n"
        f'<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="{_esc(lang)}">\n'
        f"<head><meta charset=\"utf-8\"/><title>{_esc(ch.title)}</title>"
        '<link rel="stylesheet" type="text/css" href="style.css"/></head>\n'
        f"<body>\n{ch.html}\n</body>\n</html>"
    )


def _nav_xhtml(book: EpubBook, files: list[str]) -> str:
    items = "\n".join(
        f'      <li><a href="{fn}">{_esc(ch.title or f"{i + 1}장")}</a></li>'
        for i, (ch, fn) in enumerate(zip(book.chapters, files))
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE html>\n'
        f'<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="{_esc(book.language)}">\n'
        f"<head><meta charset=\"utf-8\"/><title>{_esc(book.title)}</title></head>\n"
        '<body>\n  <nav epub:type="toc" id="toc">\n    <h1>목차</h1>\n    <ol>\n'
        f"{items}\n    </ol>\n  </nav>\n</body>\n</html>"
    )


def _opf(book: EpubBook, files: list[str], modified: str) -> str:
    manifest = [
        '    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
        '    <item id="css" href="style.css" media-type="text/css"/>',
    ]
    spine = []
    for i, fn in enumerate(files):
        manifest.append(f'    <item id="chap{i}" href="{fn}" media-type="application/xhtml+xml"/>')
        spine.append(f'    <itemref idref="chap{i}"/>')
    creator = f"    <dc:creator>{_esc(book.author)}</dc:creator>\n" if book.author else ""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid" xml:lang="{_esc(book.language)}">\n'
        '  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
        f"    <dc:identifier id=\"bookid\">{_esc(book.identifier)}</dc:identifier>\n"
        f"    <dc:title>{_esc(book.title)}</dc:title>\n"
        f"    <dc:language>{_esc(book.language)}</dc:language>\n"
        f"{creator}    <dc:publisher>{PUBLISHER}</dc:publisher>\n"
        f'    <meta property="dcterms:modified">{_esc(modified)}</meta>\n'
        "  </metadata>\n"
        "  <manifest>\n" + "\n".join(manifest) + "\n  </manifest>\n"
        "  <spine>\n" + "\n".join(spine) + "\n  </spine>\n"
        "</package>"
    )


def build_epub(book: EpubBook, modified: str) -> bytes:
    """EpubBook → EPUB3 zip 바이트. modified = ISO8601 UTC (예: 2026-06-19T12:00:00Z)."""
    files = [f"chap_{i}.xhtml" for i in range(len(book.chapters))]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        # mimetype은 반드시 첫 엔트리 + 비압축(STORED)
        z.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml", _CONTAINER)
        z.writestr("OEBPS/style.css", _CSS)
        z.writestr("OEBPS/package.opf", _opf(book, files, modified))
        z.writestr("OEBPS/nav.xhtml", _nav_xhtml(book, files))
        for ch, fn in zip(book.chapters, files):
            z.writestr(f"OEBPS/{fn}", _chapter_xhtml(ch, book.language))
    return buf.getvalue()
