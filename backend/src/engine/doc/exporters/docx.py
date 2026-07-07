"""DOCX (OOXML) exporter — UniversalDoc(IR) → ``.docx`` bytes (순수 stdlib).

수출 2호. ``zipfile``/``xml`` 만 사용한다(python-docx 등 외부 의존 없음).

계약
----
    export_docx(doc: UniversalDoc, title: str,
                images: dict[str, bytes] | None = None) -> bytes

``images`` 는 IMAGE 블록의 정본 ``src``(예: ``/media/{key}``) → 원본 바이트 매핑이다.
있으면 ``word/media/`` 에 임베드하고 ``w:drawing`` 으로 참조하며, 없으면(또는 매핑에
없으면) alt 텍스트 문단으로 폴백한다 — 수출 자체는 항상 성공한다. 이미지 IO(정본
HTML 의 src → 바이트 resolve)는 서비스 계층 몫이고 exporter 는 IR + bytes 만 받는다.

산출 OOXML(WordprocessingML) 최소 패키지::

    [Content_Types].xml           (파트별 content-type)
    _rels/.rels                   (officeDocument → word/document.xml, core-properties)
    docProps/core.xml             (dc:title)
    word/document.xml             (본문 — w: 네임스페이스)
    word/_rels/document.xml.rels  (styles/numbering + 이미지 관계)
    word/styles.xml               (Heading{1-6}/Quote/Code/ListParagraph/TableGrid)
    word/numbering.xml            (bullet=numId1 / decimal=numId2)
    word/media/imageN.ext         (임베드 이미지, 있을 때만)

설계 메모
---------
- exporter 는 엔진 레이어라 IO/HTTP 를 모른다 — 순수하게 bytes 만 만든다.
- 인라인 서식(strong/em/u)은 정본 인라인 조각을 dialect 의 DOM 빌더(``_build_dom``)로
  파싱해 run(``w:r``) 서식(``w:b``/``w:i``/``w:u``)으로 복원한다 — 단일 소스.
- 표의 colspan → ``w:gridSpan``, rowspan → ``w:vMerge``(restart/continue). vMerge 는
  피복 셀에 연속 셀을 실제로 채워야 하므로 dialect 의 ``iter_table_rows``(피복 생략)
  대신 격자를 직접 걸어 연속 셀을 방출한다.
- XML 유효성만 보장한다(실제 Word 없이 zipfile+ElementTree 로 검증) — 렌더 충실도는
  스타일 정의(styles.xml)에 위임한다.
"""
from __future__ import annotations

import io
import struct
import zipfile
from datetime import UTC, datetime
from html import escape

from src.engine.doc.dialect import _build_dom  # 정본 인라인 조각 → DOM(단일 파서 소스).
from src.engine.doc.models import Block, BlockType, UniversalDoc

# ── 네임스페이스 ───────────────────────────────────────────────
_NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_NS_WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
_NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_NS_PIC = "http://schemas.openxmlformats.org/drawingml/2006/picture"
_NS_CT = "http://schemas.openxmlformats.org/package/2006/content-types"
_NS_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
_NS_CP = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
_NS_DC = "http://purl.org/dc/elements/1.1/"
_NS_DCTERMS = "http://purl.org/dc/terms/"
_NS_XSI = "http://www.w3.org/2001/XMLSchema-instance"

_REL_OFFICE = f"{_NS_R}/officeDocument"
_REL_CORE = f"{_NS_REL}/metadata/core-properties"
_REL_STYLES = f"{_NS_R}/styles"
_REL_NUMBERING = f"{_NS_R}/numbering"
_REL_IMAGE = f"{_NS_R}/image"

_DOC_NS_DECLS = (
    f'xmlns:w="{_NS_W}" xmlns:r="{_NS_R}" xmlns:wp="{_NS_WP}"'
)

# EMU(English Metric Unit) 변환 — 96dpi 기준 px→EMU, 본문 폭 상한(6인치).
_EMU_PER_PX = 9525
_MAX_WIDTH_EMU = 6 * 914400  # 6인치 = A4 여백 제외 본문 폭 근사.
_DEFAULT_PX = (400, 300)  # 치수 미상 이미지 기본 박스.

_HEADING_HALF_PT = {1: 64, 2: 56, 3: 48, 4: 40, 5: 32, 6: 28}
_INLINE_ALIASES = {"b": "strong", "i": "em"}
_ALIGN_TO_JC = {"left": "left", "right": "right", "center": "center", "justify": "both"}


# ── 이스케이프 ─────────────────────────────────────────────────


def _t(text: str) -> str:
    """XML 텍스트 노드 이스케이프(& < > 및 따옴표까지 — XML 상 무해)."""
    return escape(text, quote=True)


# ── 인라인 조각 → run 목록 ─────────────────────────────────────


def _iter_runs(content: str) -> list[tuple[str, frozenset[str]]]:
    """정본 인라인 조각을 ``(text, fmt)`` run 목록으로. fmt ⊆ {'b','i','u'}.

    dialect 의 화이트리스트(strong/em/u/a, b/i→strong/em 정규화)와 동일한 파서를
    재사용한다 — a 는 서식 없는 텍스트 run 으로(하이퍼링크 관계는 v1 범위 밖).
    """
    runs: list[tuple[str, frozenset[str]]] = []

    def walk(nodes: list, fmt: frozenset[str]) -> None:
        for node in nodes:
            if node.tag is None:
                if node.text:
                    runs.append((node.text, fmt))
                continue
            tag = _INLINE_ALIASES.get(node.tag, node.tag)
            nfmt = fmt
            if tag == "strong":
                nfmt = fmt | {"b"}
            elif tag == "em":
                nfmt = fmt | {"i"}
            elif tag == "u":
                nfmt = fmt | {"u"}
            walk(node.children, nfmt)

    walk(_build_dom(content), frozenset())
    return runs


def _run_xml(text: str, fmt: frozenset[str]) -> str:
    if not text:
        return ""
    props: list[str] = []
    if "b" in fmt:
        props.append("<w:b/>")
    if "i" in fmt:
        props.append("<w:i/>")
    if "u" in fmt:
        props.append('<w:u w:val="single"/>')
    rpr = f"<w:rPr>{''.join(props)}</w:rPr>" if props else ""
    return f'<w:r>{rpr}<w:t xml:space="preserve">{_t(text)}</w:t></w:r>'


def _runs_xml(content: str) -> str:
    return "".join(_run_xml(text, fmt) for text, fmt in _iter_runs(content))


def _ppr(*, pstyle: str | None = None, style: dict | None = None) -> str:
    parts: list[str] = []
    if pstyle:
        parts.append(f'<w:pStyle w:val="{pstyle}"/>')
    align = (style or {}).get("align")
    jc = _ALIGN_TO_JC.get(align) if align else None
    if jc:
        parts.append(f'<w:jc w:val="{jc}"/>')
    return f"<w:pPr>{''.join(parts)}</w:pPr>" if parts else ""


# ── 이미지 스니핑(순수 stdlib) ────────────────────────────────


def _image_ext(data: bytes) -> str | None:
    """매직바이트로 확장자 결정(png/jpeg/gif/webp). 미지원이면 None."""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:2] == b"\xff\xd8":
        return "jpeg"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def _png_size(data: bytes) -> tuple[int, int] | None:
    if len(data) >= 24 and data[12:16] == b"IHDR":
        w, h = struct.unpack(">II", data[16:24])
        return w, h
    return None


def _gif_size(data: bytes) -> tuple[int, int] | None:
    if len(data) >= 10:
        w, h = struct.unpack("<HH", data[6:10])
        return w, h
    return None


def _jpeg_size(data: bytes) -> tuple[int, int] | None:
    i, n = 2, len(data)
    while i + 9 < n:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        # SOF0..SOF15(치수 있음) — 단, DHT/DAC/RST/SOI/EOI 제외.
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                      0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            h, w = struct.unpack(">HH", data[i + 5:i + 9])
            return w, h
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        seg_len = struct.unpack(">H", data[i + 2:i + 4])[0]
        i += 2 + seg_len
    return None


def _webp_size(data: bytes) -> tuple[int, int] | None:
    fourcc = data[12:16]
    try:
        if fourcc == b"VP8X":
            w = int.from_bytes(data[24:27], "little") + 1
            h = int.from_bytes(data[27:30], "little") + 1
            return w, h
        if fourcc == b"VP8L":
            b = data[21:25]
            bits = int.from_bytes(b, "little")
            w = (bits & 0x3FFF) + 1
            h = ((bits >> 14) & 0x3FFF) + 1
            return w, h
        if fourcc == b"VP8 ":
            w = struct.unpack("<H", data[26:28])[0] & 0x3FFF
            h = struct.unpack("<H", data[28:30])[0] & 0x3FFF
            return w, h
    except (struct.error, IndexError):
        return None
    return None


def _image_px(data: bytes, ext: str) -> tuple[int, int]:
    """픽셀 치수 — 파싱 실패 시 기본 박스."""
    try:
        size = {
            "png": _png_size,
            "jpeg": _jpeg_size,
            "gif": _gif_size,
            "webp": _webp_size,
        }[ext](data)
    except (struct.error, IndexError):
        size = None
    if not size or size[0] <= 0 or size[1] <= 0:
        return _DEFAULT_PX
    return size


def _emu_extent(px: tuple[int, int]) -> tuple[int, int]:
    """px 치수 → EMU (본문 폭 상한 내에서 비율 유지 축소)."""
    cx = px[0] * _EMU_PER_PX
    cy = px[1] * _EMU_PER_PX
    if cx > _MAX_WIDTH_EMU:
        cy = round(cy * _MAX_WIDTH_EMU / cx)
        cx = _MAX_WIDTH_EMU
    return cx, cy


def _drawing_xml(rid: str, cx: int, cy: int, pic_id: int) -> str:
    """인라인 그림 run 을 감싼 문단(w:p)."""
    return (
        "<w:p><w:r><w:drawing>"
        '<wp:inline distT="0" distB="0" distL="0" distR="0">'
        f'<wp:extent cx="{cx}" cy="{cy}"/>'
        '<wp:effectExtent l="0" t="0" r="0" b="0"/>'
        f'<wp:docPr id="{pic_id}" name="Picture {pic_id}"/>'
        "<wp:cNvGraphicFramePr>"
        f'<a:graphicFrameLocks xmlns:a="{_NS_A}" noChangeAspect="1"/>'
        "</wp:cNvGraphicFramePr>"
        f'<a:graphic xmlns:a="{_NS_A}">'
        f'<a:graphicData uri="{_NS_PIC}">'
        f'<pic:pic xmlns:pic="{_NS_PIC}">'
        "<pic:nvPicPr>"
        f'<pic:cNvPr id="{pic_id}" name="Picture {pic_id}"/>'
        "<pic:cNvPicPr/>"
        "</pic:nvPicPr>"
        "<pic:blipFill>"
        f'<a:blip r:embed="{rid}"/>'
        "<a:stretch><a:fillRect/></a:stretch>"
        "</pic:blipFill>"
        "<pic:spPr>"
        '<a:xfrm><a:off x="0" y="0"/>'
        f'<a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
        "</pic:spPr>"
        "</pic:pic>"
        "</a:graphicData>"
        "</a:graphic>"
        "</wp:inline>"
        "</w:drawing></w:r></w:p>"
    )


# ── 표 조립 ────────────────────────────────────────────────────


def _tbl_pr() -> str:
    borders = "".join(
        f'<w:{side} w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
        for side in ("top", "left", "bottom", "right", "insideH", "insideV")
    )
    return (
        '<w:tblPr><w:tblStyle w:val="TableGrid"/>'
        '<w:tblW w:w="0" w:type="auto"/>'
        f"<w:tblBorders>{borders}</w:tblBorders>"
        "</w:tblPr>"
    )


def _tbl_grid(col_count: int) -> str:
    return "<w:tblGrid>" + "<w:gridCol/>" * max(1, col_count) + "</w:tblGrid>"


def _tc(content: str, *, gridspan: int = 1, vmerge: str | None = None) -> str:
    props: list[str] = []
    if gridspan > 1:
        props.append(f'<w:gridSpan w:val="{gridspan}"/>')
    if vmerge == "restart":
        props.append('<w:vMerge w:val="restart"/>')
    elif vmerge == "continue":
        props.append("<w:vMerge/>")
    tcpr = f"<w:tcPr>{''.join(props)}</w:tcPr>" if props else ""
    return f"<w:tc>{tcpr}{content or '<w:p/>'}</w:tc>"


def _text_p(text: str, *, bold: bool = False) -> str:
    fmt = frozenset({"b"}) if bold else frozenset()
    return f"<w:p>{_run_xml(text, fmt)}</w:p>"


# ── 빌더 ───────────────────────────────────────────────────────


class _Builder:
    """본문 + 이미지 파트/관계를 누적한다(이미지가 rId·media 파트를 낳으므로 상태 필요)."""

    def __init__(self, images: dict[str, bytes] | None) -> None:
        self._images = images or {}
        self._body: list[str] = []
        self._media: dict[str, bytes] = {}
        self._img_rels: list[tuple[str, str]] = []  # (rId, target)
        self._img_n = 0

    # ── 이미지 관계 등록 ───────────────────────────────────────
    def _add_image(self, data: bytes, ext: str) -> tuple[str, int]:
        self._img_n += 1
        fname = f"image{self._img_n}.{ext}"
        self._media[fname] = data
        rid = f"rIdImg{self._img_n}"
        self._img_rels.append((rid, f"media/{fname}"))
        return rid, self._img_n

    def _image_block(self, block: Block) -> str:
        src = block.meta.get("src", "")
        data = self._images.get(src)
        if data:
            ext = _image_ext(data)
            if ext:
                rid, pic_id = self._add_image(data, ext)
                cx, cy = _emu_extent(_image_px(data, ext))
                return _drawing_xml(rid, cx, cy, pic_id)
        # 폴백: 매핑 없음/미지원 포맷 → alt 텍스트 문단(수출은 성공).
        alt = block.meta.get("alt", "") or "[이미지]"
        return _text_p(alt)

    # ── 블록 방출 ──────────────────────────────────────────────
    def add_block(self, block: Block) -> None:
        t = block.type
        m = block.meta

        if t == BlockType.HEADING:
            level = max(1, min(6, int(m.get("level", 1))))
            self._body.append(
                f"<w:p>{_ppr(pstyle=f'Heading{level}')}{_runs_xml(block.content)}</w:p>"
            )
        elif t == BlockType.PARAGRAPH:
            self._body.append(
                f"<w:p>{_ppr(style=m.get('style'))}{_runs_xml(block.content)}</w:p>"
            )
        elif t == BlockType.QUOTE:
            self._body.append(
                f"<w:p>{_ppr(pstyle='Quote')}{_runs_xml(block.content)}</w:p>"
            )
        elif t == BlockType.LIST:
            num_id = "2" if m.get("ordered") else "1"
            ppr = (
                '<w:pPr><w:pStyle w:val="ListParagraph"/>'
                f'<w:numPr><w:ilvl w:val="0"/><w:numId w:val="{num_id}"/></w:numPr>'
                "</w:pPr>"
            )
            for item in block.content.split("\n"):
                if item:
                    self._body.append(f"<w:p>{ppr}{_runs_xml(item)}</w:p>")
        elif t == BlockType.CODE:
            ppr = '<w:pPr><w:pStyle w:val="Code"/></w:pPr>'
            for line in block.content.split("\n"):
                run = (
                    f'<w:r><w:t xml:space="preserve">{_t(line)}</w:t></w:r>'
                    if line
                    else ""
                )
                self._body.append(f"<w:p>{ppr}{run}</w:p>")
        elif t == BlockType.IMAGE:
            self._body.append(self._image_block(block))
        elif t == BlockType.TABLE:
            self._body.append(self._table_xml(m))
        else:
            self._body.append(f"<w:p>{_runs_xml(block.content)}</w:p>")

    # ── 표 ────────────────────────────────────────────────────
    def _table_xml(self, m: dict) -> str:
        if m.get("cells"):
            return self._styled_table(m)
        return self._simple_table(m)

    @staticmethod
    def _simple_table(m: dict) -> str:
        headers = m.get("headers", [])
        rows = m.get("rows", [])
        col_count = max([len(headers), *(len(r) for r in rows), 1])
        parts = ["<w:tbl>", _tbl_pr(), _tbl_grid(col_count)]
        if headers:
            cells = "".join(_tc(_text_p(h, bold=True)) for h in headers)
            parts.append(f"<w:tr>{cells}</w:tr>")
        for row in rows:
            cells = "".join(_tc(_text_p(c)) for c in row)
            parts.append(f"<w:tr>{cells}</w:tr>")
        parts.append("</w:tbl>")
        return "".join(parts)

    @staticmethod
    def _cell_content(cell: dict) -> str:
        style = cell.get("style") or {}
        fmt: set[str] = set()
        if style.get("bold"):
            fmt.add("b")
        if style.get("italic"):
            fmt.add("i")
        if style.get("underline"):
            fmt.add("u")
        run = _run_xml(cell.get("text", ""), frozenset(fmt))
        return f"<w:p>{_ppr(style=style)}{run}</w:p>"

    def _styled_table(self, m: dict) -> str:
        cells = m["cells"]
        row_count = max(1, int(m.get("row_count", 1)))
        col_count = max(1, int(m.get("col_count", 1)))
        owner: dict[tuple[int, int], tuple[int, int]] = {}
        cell_at: dict[tuple[int, int], dict] = {}
        for cell in cells:
            r, c = int(cell.get("row", 0)), int(cell.get("col", 0))
            cell_at[(r, c)] = cell
            rs, cs = int(cell.get("rowspan", 1)), int(cell.get("colspan", 1))
            for dr in range(rs):
                for dc in range(cs):
                    owner[(r + dr, c + dc)] = (r, c)

        parts = ["<w:tbl>", _tbl_pr(), _tbl_grid(col_count)]
        for r in range(row_count):
            row: list[str] = ["<w:tr>"]
            c = 0
            while c < col_count:
                start = owner.get((r, c))
                if start is None:
                    row.append(_tc("<w:p/>"))
                    c += 1
                    continue
                sr, sc = start
                cell = cell_at[(sr, sc)]
                cs = max(1, int(cell.get("colspan", 1)))
                rs = max(1, int(cell.get("rowspan", 1)))
                if sr == r:
                    vmerge = "restart" if rs > 1 else None
                    row.append(_tc(self._cell_content(cell), gridspan=cs, vmerge=vmerge))
                else:
                    row.append(_tc("<w:p/>", gridspan=cs, vmerge="continue"))
                c += cs
            row.append("</w:tr>")
            parts.append("".join(row))
        parts.append("</w:tbl>")
        return "".join(parts)

    # ── 파트 직렬화 ────────────────────────────────────────────
    def document_xml(self) -> str:
        sect = (
            "<w:sectPr>"
            '<w:pgSz w:w="11906" w:h="16838"/>'
            '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"'
            ' w:header="708" w:footer="708" w:gutter="0"/>'
            "</w:sectPr>"
        )
        body = "".join(self._body)
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            f"<w:document {_DOC_NS_DECLS}>"
            f"<w:body>{body}{sect}</w:body>"
            "</w:document>"
        )

    def document_rels_xml(self) -> str:
        rels = [
            f'<Relationship Id="rId1" Type="{_REL_STYLES}" Target="styles.xml"/>',
            f'<Relationship Id="rId2" Type="{_REL_NUMBERING}" Target="numbering.xml"/>',
        ]
        rels += [
            f'<Relationship Id="{rid}" Type="{_REL_IMAGE}" Target="{target}"/>'
            for rid, target in self._img_rels
        ]
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            f'<Relationships xmlns="{_NS_REL}">{"".join(rels)}</Relationships>'
        )

    @property
    def media(self) -> dict[str, bytes]:
        return self._media


# ── 정적 파트 ──────────────────────────────────────────────────


def _content_types_xml() -> str:
    defaults = "".join(
        f'<Default Extension="{ext}" ContentType="{ct}"/>'
        for ext, ct in (
            ("rels", "application/vnd.openxmlformats-package.relationships+xml"),
            ("xml", "application/xml"),
            ("png", "image/png"),
            ("jpeg", "image/jpeg"),
            ("jpg", "image/jpeg"),
            ("gif", "image/gif"),
            ("webp", "image/webp"),
        )
    )
    overrides = "".join(
        f'<Override PartName="{part}" ContentType="{ct}"/>'
        for part, ct in (
            (
                "/word/document.xml",
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document.main+xml",
            ),
            (
                "/word/styles.xml",
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.styles+xml",
            ),
            (
                "/word/numbering.xml",
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.numbering+xml",
            ),
            (
                "/docProps/core.xml",
                "application/vnd.openxmlformats-package.core-properties+xml",
            ),
        )
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        f'<Types xmlns="{_NS_CT}">{defaults}{overrides}</Types>'
    )


def _root_rels_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        f'<Relationships xmlns="{_NS_REL}">'
        f'<Relationship Id="rId1" Type="{_REL_OFFICE}" Target="word/document.xml"/>'
        f'<Relationship Id="rId2" Type="{_REL_CORE}" Target="docProps/core.xml"/>'
        "</Relationships>"
    )


def _core_xml(title: str) -> str:
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        f'<cp:coreProperties xmlns:cp="{_NS_CP}" xmlns:dc="{_NS_DC}"'
        f' xmlns:dcterms="{_NS_DCTERMS}" xmlns:xsi="{_NS_XSI}">'
        f"<dc:title>{_t(title)}</dc:title>"
        f'<dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>'
        f'<dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>'
        "</cp:coreProperties>"
    )


def _styles_xml() -> str:
    styles = [
        '<w:style w:type="paragraph" w:default="1" w:styleId="Normal">'
        '<w:name w:val="Normal"/></w:style>',
    ]
    for level, half_pt in _HEADING_HALF_PT.items():
        styles.append(
            f'<w:style w:type="paragraph" w:styleId="Heading{level}">'
            f'<w:name w:val="heading {level}"/><w:basedOn w:val="Normal"/>'
            f'<w:pPr><w:keepNext/><w:outlineLvl w:val="{level - 1}"/></w:pPr>'
            f'<w:rPr><w:b/><w:sz w:val="{half_pt}"/></w:rPr></w:style>'
        )
    styles.append(
        '<w:style w:type="paragraph" w:styleId="Quote">'
        '<w:name w:val="Quote"/><w:basedOn w:val="Normal"/>'
        '<w:pPr><w:ind w:left="720"/></w:pPr>'
        '<w:rPr><w:i/><w:color w:val="404040"/></w:rPr></w:style>'
    )
    styles.append(
        '<w:style w:type="paragraph" w:styleId="Code">'
        '<w:name w:val="Code"/><w:basedOn w:val="Normal"/>'
        '<w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas" w:cs="Consolas"/>'
        "</w:rPr></w:style>"
    )
    styles.append(
        '<w:style w:type="paragraph" w:styleId="ListParagraph">'
        '<w:name w:val="List Paragraph"/><w:basedOn w:val="Normal"/></w:style>'
    )
    styles.append(
        '<w:style w:type="table" w:styleId="TableGrid">'
        '<w:name w:val="Table Grid"/></w:style>'
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        f'<w:styles xmlns:w="{_NS_W}">{"".join(styles)}</w:styles>'
    )


def _numbering_xml() -> str:
    def _abstract(aid: int, fmt: str, text: str) -> str:
        return (
            f'<w:abstractNum w:abstractNumId="{aid}">'
            '<w:lvl w:ilvl="0"><w:start w:val="1"/>'
            f'<w:numFmt w:val="{fmt}"/><w:lvlText w:val="{text}"/>'
            '<w:lvlJc w:val="left"/>'
            '<w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr>'
            "</w:lvl></w:abstractNum>"
        )

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        f'<w:numbering xmlns:w="{_NS_W}">'
        + _abstract(0, "bullet", "•")
        + _abstract(1, "decimal", "%1.")
        + '<w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>'
        + '<w:num w:numId="2"><w:abstractNumId w:val="1"/></w:num>'
        + "</w:numbering>"
    )


# ── ZIP 조립 ───────────────────────────────────────────────────


def export_docx(
    doc: UniversalDoc, title: str, images: dict[str, bytes] | None = None
) -> bytes:
    """UniversalDoc → DOCX(OOXML) bytes.

    ``title`` 은 docProps/core.xml 의 dc:title. ``images`` 는 IMAGE 블록 정본 src →
    원본 바이트 매핑(없으면 alt 폴백). 반환값을 그대로 파일로 쓰면 유효한 ``.docx`` —
    파일명·다운로드 헤더는 호출자(서비스/표현)가 붙인다.
    """
    safe_title = (title or "").strip() or "Untitled"
    builder = _Builder(images)
    for page in doc.pages:
        for block in page.blocks:
            builder.add_block(block)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _content_types_xml())
        zf.writestr("_rels/.rels", _root_rels_xml())
        zf.writestr("docProps/core.xml", _core_xml(safe_title))
        zf.writestr("word/document.xml", builder.document_xml())
        zf.writestr("word/_rels/document.xml.rels", builder.document_rels_xml())
        zf.writestr("word/styles.xml", _styles_xml())
        zf.writestr("word/numbering.xml", _numbering_xml())
        for fname, data in builder.media.items():
            zf.writestr(f"word/media/{fname}", data)
    return buf.getvalue()
