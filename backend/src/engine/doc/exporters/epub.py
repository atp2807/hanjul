"""EPUB 3 exporter — UniversalDoc(IR) → ``.epub`` bytes (순수 stdlib).

수출 1호. ``zipfile``/``xml``/``html`` 만 사용한다(외부 의존 없음).

계약
----
    export_epub(doc: UniversalDoc, title: str) -> bytes

산출 EPUB 3 구조::

    mimetype                 (무압축, ZIP 첫 엔트리, "application/epub+zip")
    META-INF/container.xml   (rootfile → OEBPS/content.opf)
    OEBPS/content.opf        (dc:title / dc:identifier=urn:uuid / dc:language=ko)
    OEBPS/nav.xhtml          (h1~h3 헤딩 기반 앵커 목차)
    OEBPS/content.xhtml      (본문 — 방언 블록을 유효한 XHTML 로)

설계 메모
---------
- exporter 는 엔진 레이어라 IO/HTTP 를 모른다 — 순수하게 bytes 만 만든다.
- 본문은 블록에서 직접 XHTML 을 만든다(dialect 수정 없이). 인라인 조각은
  dialect 의 정본 인라인 렌더러(``_serialize_inline``)를 재사용해 이스케이프·
  화이트리스트(strong/em/u/a)를 단일 소스로 유지한다 — 결과는 유효한 XHTML 이다.
- 챕터 분할 v1: 없음 — 단일 content.xhtml + nav 는 헤딩 앵커 목차.
- 이미지 v2: ``images`` 매핑(정본 src → 원본 bytes)이 주어지면 ``OEBPS/images/`` 에
  임베드하고 ``<img/>`` 로 참조하며 OPF manifest 에 등록한다. 매핑에 없으면(또는
  images 자체가 없으면) 종전처럼 alt 텍스트만 남긴다 — 수출은 항상 성공한다.
  이미지 IO(src→bytes resolve)는 서비스 계층 몫이고 exporter 는 IR + bytes 만 받는다.
"""
from __future__ import annotations

import io
import uuid
import zipfile
from datetime import UTC, datetime
from html import escape

from src.engine.doc.dialect import (
    _serialize_inline,  # 정본 인라인 렌더러 재사용(이스케이프+strong/em/u/a 화이트리스트).
    iter_table_rows,
    style_to_css,
)
from src.engine.doc.models import Block, BlockType, UniversalDoc

_MIMETYPE = "application/epub+zip"
_CONTAINER_PATH = "META-INF/container.xml"
_OPF_PATH = "OEBPS/content.opf"
_NAV_PATH = "OEBPS/nav.xhtml"
_CONTENT_PATH = "OEBPS/content.xhtml"
_IMAGES_DIR = "OEBPS/images"
_LANG = "ko"
# nav 목차에 넣을 헤딩 최대 레벨(h1~h3).
_TOC_MAX_LEVEL = 3


def _image_media_type(data: bytes) -> tuple[str, str] | None:
    """매직바이트로 ``(확장자, content-type)`` 결정. 미지원이면 None(alt 폴백).

    manifest media-type 은 EPUB 리더가 이미지를 디코드하는 근거이므로 실제 바이트에서
    판별한다(src 확장자 신뢰 금지 — webp/png/jpg/gif 지원).
    """
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png", "image/png"
    if data[:2] == b"\xff\xd8":
        return "jpg", "image/jpeg"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif", "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp", "image/webp"
    return None


# ── XML 문서 조각 ──────────────────────────────────────────────


def _container_xml() -> str:
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<container version="1.0" '
        'xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n'
        "  <rootfiles>\n"
        f'    <rootfile full-path="{_OPF_PATH}" '
        'media-type="application/oebps-package+xml"/>\n'
        "  </rootfiles>\n"
        "</container>\n"
    )


def _opf_xml(title: str, book_id: str, image_items: list[tuple[str, str, str]]) -> str:
    modified = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    esc_title = escape(title, quote=True)
    # image_items: [(item_id, href_relative_to_opf, media_type), ...]
    image_manifest = "".join(
        f'    <item id="{item_id}" href="{href}" media-type="{media_type}"/>\n'
        for item_id, href, media_type in image_items
    )
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" '
        f'unique-identifier="pub-id" xml:lang="{_LANG}">\n'
        '  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
        f"    <dc:title>{esc_title}</dc:title>\n"
        f'    <dc:identifier id="pub-id">urn:uuid:{book_id}</dc:identifier>\n'
        f"    <dc:language>{_LANG}</dc:language>\n"
        f'    <meta property="dcterms:modified">{modified}</meta>\n'
        "  </metadata>\n"
        "  <manifest>\n"
        '    <item id="nav" href="nav.xhtml" '
        'media-type="application/xhtml+xml" properties="nav"/>\n'
        '    <item id="content" href="content.xhtml" '
        'media-type="application/xhtml+xml"/>\n'
        f"{image_manifest}"
        "  </manifest>\n"
        "  <spine>\n"
        '    <itemref idref="content"/>\n'
        "  </spine>\n"
        "</package>\n"
    )


def _xhtml_shell(title: str, body: str, *, extra_ns: str = "") -> str:
    esc_title = escape(title, quote=True)
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml"'
        f'{extra_ns} xml:lang="{_LANG}" lang="{_LANG}">\n'
        f"<head><meta charset=\"utf-8\"/><title>{esc_title}</title></head>\n"
        f"<body>\n{body}\n</body>\n</html>\n"
    )


def _nav_xhtml(title: str, toc: list[tuple[str, str]]) -> str:
    # toc: [(anchor_id, inline_label), ...]. 헤딩이 없으면 본문 단일 항목으로 폴백
    # (EPUB 3 nav 는 toc 안에 최소 1개 링크가 필요).
    if toc:
        items = "\n".join(
            f'    <li><a href="content.xhtml#{anchor}">{label}</a></li>'
            for anchor, label in toc
        )
    else:
        items = (
            f'    <li><a href="content.xhtml">{escape(title)}</a></li>'
        )
    body = (
        '<nav epub:type="toc" id="toc">\n'
        "  <h1>목차</h1>\n"
        "  <ol>\n"
        f"{items}\n"
        "  </ol>\n"
        "</nav>"
    )
    return _xhtml_shell(
        title, body, extra_ns=' xmlns:epub="http://www.idpf.org/2007/ops"'
    )


# ── 블록 → XHTML ───────────────────────────────────────────────


def _render_styled_table(meta: dict) -> str:
    cells = meta["cells"]
    row_count = meta.get("row_count", 1)
    col_count = meta.get("col_count", 1)
    parts: list[str] = ["<table>"]
    for _row_idx, row in iter_table_rows(cells, row_count, col_count):
        parts.append("<tr>")
        for _col_idx, cell in row:
            if cell is None:
                parts.append("<td></td>")
                continue
            attrs: list[str] = []
            cs = cell.get("colspan", 1)
            rs = cell.get("rowspan", 1)
            if cs > 1:
                attrs.append(f'colspan="{cs}"')
            if rs > 1:
                attrs.append(f'rowspan="{rs}"')
            css = style_to_css(cell["style"]) if cell.get("style") else ""
            if css:
                attrs.append(f'style="{escape(css, quote=True)}"')
            attr_str = (" " + " ".join(attrs)) if attrs else ""
            parts.append(f"<td{attr_str}>{escape(cell.get('text', ''))}</td>")
        parts.append("</tr>")
    parts.append("</table>")
    return "".join(parts)


def _render_simple_table(meta: dict) -> str:
    headers = meta.get("headers", [])
    rows = meta.get("rows", [])
    thead = "<tr>" + "".join(f"<th>{escape(h)}</th>" for h in headers) + "</tr>"
    tbody = "".join(
        "<tr>" + "".join(f"<td>{escape(c)}</td>" for c in row) + "</tr>"
        for row in rows
    )
    return f"<table><thead>{thead}</thead><tbody>{tbody}</tbody></table>"


class _ImageEmbedder:
    """정본 src → bytes 매핑을 받아 이미지를 OEBPS/images/ 에 임베드한다.

    같은 src 는 한 번만 임베드(중복 제거)하고 재사용한다. manifest 항목과 자산 바이트를
    누적하며, 매핑에 없거나 미지원 포맷이면 None 을 돌려줘 호출부가 alt 로 폴백한다.
    """

    def __init__(self, images: dict[str, bytes] | None) -> None:
        self._images = images or {}
        self._by_src: dict[str, str] = {}  # src → images/ 상대 href
        self._assets: list[tuple[str, bytes]] = []  # (zip 경로, bytes)
        self._manifest: list[tuple[str, str, str]] = []  # (item_id, href, media_type)
        self._n = 0

    def href_for(self, src: str) -> str | None:
        """src 에 대한 content.xhtml 기준 상대 href. 임베드 불가면 None."""
        if src in self._by_src:
            return self._by_src[src]
        data = self._images.get(src)
        if not data:
            return None
        sniffed = _image_media_type(data)
        if sniffed is None:
            return None
        ext, media_type = sniffed
        self._n += 1
        filename = f"image{self._n}.{ext}"
        href = f"images/{filename}"  # content.xhtml(OEBPS/) 기준 상대경로
        self._by_src[src] = href
        self._assets.append((f"{_IMAGES_DIR}/{filename}", data))
        self._manifest.append((f"img{self._n}", href, media_type))
        return href

    @property
    def assets(self) -> list[tuple[str, bytes]]:
        return self._assets

    @property
    def manifest_items(self) -> list[tuple[str, str, str]]:
        return self._manifest


def _render_block(block: Block, anchor: str | None, embedder: _ImageEmbedder) -> str:
    """블록 하나를 유효한 XHTML 문자열로. ``anchor`` 는 헤딩에만 붙는 id."""
    t = block.type
    m = block.meta

    if t == BlockType.HEADING:
        level = max(1, min(6, int(m.get("level", 1))))
        inner = _serialize_inline(block.content)
        id_attr = f' id="{anchor}"' if anchor else ""
        return f"<h{level}{id_attr}>{inner}</h{level}>"

    if t == BlockType.PARAGRAPH:
        css = style_to_css(m["style"]) if m.get("style") else ""
        inner = _serialize_inline(block.content)
        if css:
            return f'<p style="{escape(css, quote=True)}">{inner}</p>'
        return f"<p>{inner}</p>"

    if t == BlockType.CODE:
        lang = m.get("language", "")
        body = escape(block.content)
        if lang:
            return (
                f'<pre><code class="language-{escape(lang, quote=True)}">'
                f"{body}</code></pre>"
            )
        return f"<pre><code>{body}</code></pre>"

    if t == BlockType.QUOTE:
        return f"<blockquote>{_serialize_inline(block.content)}</blockquote>"

    if t == BlockType.LIST:
        tag = "ol" if m.get("ordered") else "ul"
        items = "".join(
            f"<li>{_serialize_inline(item)}</li>"
            for item in block.content.split("\n")
            if item
        )
        return f"<{tag}>{items}</{tag}>"

    if t == BlockType.IMAGE:
        alt = m.get("alt", "")
        href = embedder.href_for(m.get("src", ""))
        if href is not None:
            # 임베드 성공 → <img/>(XHTML 자기닫음)으로 상대경로 참조.
            return (
                f'<img src="{escape(href, quote=True)}" '
                f'alt="{escape(alt, quote=True)}"/>'
            )
        # 매핑 없음/미지원 포맷 → alt 텍스트 문단 폴백(수출은 성공).
        return f'<p class="juldoc-image">{escape(alt or "[이미지]")}</p>'

    if t == BlockType.TABLE:
        if m.get("cells"):
            return _render_styled_table(m)
        return _render_simple_table(m)

    return f"<p>{_serialize_inline(block.content)}</p>"


def _build_body_and_toc(
    doc: UniversalDoc, embedder: _ImageEmbedder
) -> tuple[str, list[tuple[str, str]]]:
    """본문 XHTML 조각과 nav 목차 항목((anchor, label))을 함께 만든다.

    IMAGE 블록은 ``embedder`` 를 통해 자산 임베드 여부를 결정한다(부수효과: 임베드된
    이미지가 embedder 의 assets/manifest 에 누적된다).
    """
    parts: list[str] = []
    toc: list[tuple[str, str]] = []
    heading_n = 0
    for page in doc.pages:
        for block in page.blocks:
            anchor: str | None = None
            if block.type == BlockType.HEADING:
                heading_n += 1
                anchor = f"sec{heading_n}"
                level = max(1, min(6, int(block.meta.get("level", 1))))
                if level <= _TOC_MAX_LEVEL:
                    toc.append((anchor, _serialize_inline(block.content)))
            parts.append(_render_block(block, anchor, embedder))
    return "\n".join(parts), toc


# ── ZIP 조립 ───────────────────────────────────────────────────


def export_epub(
    doc: UniversalDoc, title: str, images: dict[str, bytes] | None = None
) -> bytes:
    """UniversalDoc → EPUB 3 bytes.

    ``title`` 은 dc:title 이자 문서 대표 제목이다. ``images`` 는 IMAGE 블록 정본 src →
    원본 바이트 매핑(있으면 OEBPS/images/ 에 임베드, 없으면 alt 폴백). 반환값은 그대로
    파일로 쓰면 유효한 ``.epub`` — 호출자(서비스/표현)가 파일명·다운로드 헤더를 붙인다.
    """
    safe_title = (title or "").strip() or "Untitled"
    book_id = str(uuid.uuid4())

    embedder = _ImageEmbedder(images)
    body, toc = _build_body_and_toc(doc, embedder)
    content_xhtml = _xhtml_shell(safe_title, body)
    nav_xhtml = _nav_xhtml(safe_title, toc)
    opf = _opf_xml(safe_title, book_id, embedder.manifest_items)
    container = _container_xml()

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # mimetype 은 반드시 첫 엔트리 + 무압축(EPUB OCF 규약).
        mimetype_info = zipfile.ZipInfo("mimetype")
        mimetype_info.compress_type = zipfile.ZIP_STORED
        zf.writestr(mimetype_info, _MIMETYPE)
        zf.writestr(_CONTAINER_PATH, container)
        zf.writestr(_OPF_PATH, opf)
        zf.writestr(_NAV_PATH, nav_xhtml)
        zf.writestr(_CONTENT_PATH, content_xhtml)
        for asset_path, asset_bytes in embedder.assets:
            zf.writestr(asset_path, asset_bytes)
    return buf.getvalue()
