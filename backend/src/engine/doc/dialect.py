"""juldoc dialect HTML v1 — lossless round-trip with UniversalDoc.

The dialect HTML is the *canonical* representation. This module owns both
directions of the contract:

    serialize_doc(doc)  -> dialect HTML string
    parse_dialect(html) -> UniversalDoc

Design notes
------------
- Document wrapper is ``<article data-juldoc="1">...</article>``. There is no
  page concept in the dialect: ``serialize_doc`` flattens all pages, and
  ``parse_dialect`` produces a single ``Page`` (or zero pages for the empty
  document, so ``UniversalDoc()`` round-trips exactly).
- Block ``content`` is a *canonical inline fragment*: plain text is escaped and
  only the inline whitelist (``strong``/``em``/``u``/``a href``) survives. Both
  serialize and parse run text through :func:`_render_inline`, so the operation
  is idempotent and safe on hand-built plain-text content too.
- ``parse_dialect`` is the sanitize defense line: ``script``/``style``/
  ``iframe``/``object``/``embed`` are dropped with their content, unknown tags
  are unwrapped (text kept), and attributes are whitelisted.
- Style in the IR (``meta["style"]`` and table-cell ``style``) is always an
  *abstract dict* (the shape the HWP parser emits: ``font``/``size``/``bold``/
  ``italic``/``underline``/``color``/``align``/``line_spacing``). Raw CSS is a
  serialization detail owned here: :func:`style_to_css` writes the abstract dict
  to a CSS string and :func:`css_to_style` reads a CSS string back to an abstract
  dict, dropping any property outside the 8-property whitelist. ``serialize_doc``
  and ``parse_dialect`` are the only style codec boundary.

Pure stdlib only (``html.parser``, ``html.escape``).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from html import escape
from html.parser import HTMLParser

from src.engine.doc.models import Block, BlockType, Page, UniversalDoc

# ── whitelists ────────────────────────────────────────────────

_INLINE_TAGS = {"strong", "em", "u", "a"}
# 정규화 매핑: b/i 는 허용 태그가 아니라 strong/em 으로 *변환*한다 (왕복 손실 방지).
# execCommand('bold'/'italic') 이 <b>/<i> 를 만드는 브라우저가 있어서 필요.
_INLINE_ALIASES = {"b": "strong", "i": "em"}
_DROP_CONTENT = {"script", "style", "iframe", "object", "embed"}
_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
_VOID_ELEMENTS = {"img", "br", "hr", "input", "meta", "link", "col", "area", "source"}
# CSS property -> abstract style key. This 8-entry map is the style whitelist:
# any CSS property not listed here is dropped on the CSS -> abstract direction.
_CSS_TO_ABSTRACT = {
    "font-family": "font",
    "font-size": "size",
    "font-weight": "bold",
    "font-style": "italic",
    "text-decoration": "underline",
    "color": "color",
    "text-align": "align",
    "line-height": "line_spacing",
}
_ALLOWED_URL_SCHEMES = {"http", "https"}
_STYLE_VALUE_BLOCKLIST = ("url(", "expression(", "javascript:")

_ARTICLE_OPEN = '<article data-juldoc="1">'
_ARTICLE_CLOSE = "</article>"


# ── minimal DOM ───────────────────────────────────────────────


@dataclass
class _Node:
    tag: str | None = None  # None marks a text node
    attrs: dict = field(default_factory=dict)
    children: list = field(default_factory=list)
    text: str = ""


class _DomBuilder(HTMLParser):
    """Builds a tolerant DOM tree from an HTML fragment."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _Node(tag="#root")
        self._stack: list[_Node] = [self.root]

    def handle_starttag(self, tag: str, attrs) -> None:
        node = _Node(tag=tag, attrs={k: (v if v is not None else "") for k, v in attrs})
        self._stack[-1].children.append(node)
        if tag not in _VOID_ELEMENTS:
            self._stack.append(node)

    def handle_startendtag(self, tag: str, attrs) -> None:
        node = _Node(tag=tag, attrs={k: (v if v is not None else "") for k, v in attrs})
        self._stack[-1].children.append(node)

    def handle_endtag(self, tag: str) -> None:
        for i in range(len(self._stack) - 1, 0, -1):
            if self._stack[i].tag == tag:
                del self._stack[i:]
                return

    def handle_data(self, data: str) -> None:
        self._stack[-1].children.append(_Node(tag=None, text=data))


def _build_dom(html: str) -> list[_Node]:
    """Parse an HTML fragment into a list of top-level nodes."""
    builder = _DomBuilder()
    builder.feed(html)
    builder.close()
    return builder.root.children


def _first_child(node: _Node, tag: str) -> _Node | None:
    for child in node.children:
        if child.tag == tag:
            return child
    return None


def _text_content(node: _Node) -> str:
    """Concatenate all descendant text (decoded)."""
    out: list[str] = []
    for child in node.children:
        if child.tag is None:
            out.append(child.text)
        else:
            out.append(_text_content(child))
    return "".join(out)


# ── sanitizers ────────────────────────────────────────────────


def _scheme_of(url: str) -> str | None:
    """Return the URL scheme (lowercased) or None when relative."""
    for i, ch in enumerate(url):
        if ch == ":":
            scheme = url[:i]
            if scheme and scheme[0].isalpha() and all(
                c.isalnum() or c in "+-." for c in scheme
            ):
                return scheme
            return None
        if ch in "/?#":
            return None
    return None


def _sanitize_url(url: str) -> str:
    """Allow relative URLs and http(s); reject everything else (e.g. javascript:)."""
    raw = url.strip()
    if not raw:
        return ""
    cleaned = "".join(ch for ch in raw if not ch.isspace() and ord(ch) >= 0x20)
    scheme = _scheme_of(cleaned.lower())
    if scheme is None:
        return raw
    if scheme in _ALLOWED_URL_SCHEMES:
        return raw
    return ""


# ── style codec (abstract dict <-> CSS) ───────────────────────


def style_to_css(style: dict) -> str:
    """Serialize an abstract style dict to a canonical CSS string.

    The abstract dict is the HWP-parser shape. Emission order is fixed so the
    codec round-trips string-identically. Values are *not* HTML-escaped here;
    callers that embed the result in an attribute must escape the whole string
    (``serialize_doc`` does). Empty/false-y properties are omitted, so a black
    color (``#000000``) and a non-positive ``line_spacing`` produce nothing.
    """
    parts: list[str] = []
    if style.get("font"):
        parts.append(f'font-family:{style["font"]}')
    if "size" in style:
        parts.append(f'font-size:{style["size"]}pt')
    if style.get("bold"):
        parts.append("font-weight:bold")
    if style.get("italic"):
        parts.append("font-style:italic")
    if style.get("underline"):
        parts.append("text-decoration:underline")
    if style.get("color") and style["color"] != "#000000":
        parts.append(f'color:{style["color"]}')
    if style.get("align"):
        parts.append(f'text-align:{style["align"]}')
    if "line_spacing" in style and style["line_spacing"] > 0:
        parts.append(f'line-height:{style["line_spacing"]}%')
    return "; ".join(parts)


def _css_font_size_to_pt(val: str) -> float | None:
    v = val.strip()
    if v.lower().endswith("pt"):
        v = v[:-2].strip()
    try:
        return float(v)
    except ValueError:
        return None


def _css_percent_to_int(val: str) -> int | None:
    v = val.strip().rstrip("%").strip()
    try:
        return int(float(v))
    except ValueError:
        return None


def css_to_style(css: str) -> dict:
    """Parse a CSS string into an abstract style dict (inverse of style_to_css).

    Only the 8 whitelisted CSS properties survive; anything else is dropped.
    Declarations whose value trips the value blocklist (``url(``/``expression(``/
    ``javascript:``) are dropped too, so this is a sanitize boundary.
    """
    style: dict = {}
    for decl in css.split(";"):
        decl = decl.strip()
        if not decl or ":" not in decl:
            continue
        prop, _, val = decl.partition(":")
        prop = prop.strip().lower()
        val = val.strip()
        key = _CSS_TO_ABSTRACT.get(prop)
        if key is None or not val:
            continue
        low = val.lower()
        if any(bad in low for bad in _STYLE_VALUE_BLOCKLIST):
            continue
        if key == "size":
            size = _css_font_size_to_pt(val)
            if size is not None:
                style["size"] = size
        elif key == "line_spacing":
            pct = _css_percent_to_int(val)
            if pct is not None:
                style["line_spacing"] = pct
        elif key == "bold":
            if "bold" in low or (low.isdigit() and int(low) >= 700):
                style["bold"] = True
        elif key == "italic":
            if "italic" in low or "oblique" in low:
                style["italic"] = True
        elif key == "underline":
            if "underline" in low:
                style["underline"] = True
        else:  # font, color, align
            style[key] = val
    return style


# ── inline rendering (canonical fragment) ─────────────────────


def _inline_start_tag(node: _Node, tag: str) -> str:
    if tag == "a":
        href = _sanitize_url(node.attrs.get("href", ""))
        if href:
            return f'<a href="{escape(href, quote=True)}">'
        return "<a>"
    return f"<{tag}>"


def _render_inline(nodes: list[_Node]) -> str:
    """Render inline DOM nodes to a canonical fragment string.

    Text is escaped; whitelisted inline tags are re-emitted with sanitized
    attributes (b/i are normalized to strong/em); drop-content tags are
    removed entirely; any other tag is unwrapped (its text is kept).
    """
    out: list[str] = []
    for node in nodes:
        if node.tag is None:
            out.append(escape(node.text))
            continue
        tag = _INLINE_ALIASES.get(node.tag, node.tag)
        if tag in _DROP_CONTENT:
            continue
        if tag in _INLINE_TAGS:
            out.append(_inline_start_tag(node, tag))
            out.append(_render_inline(node.children))
            out.append(f"</{tag}>")
        else:
            out.append(_render_inline(node.children))
    return "".join(out)


def _serialize_inline(content: str) -> str:
    """Canonicalize a block's content string into a safe inline fragment."""
    return _render_inline(_build_dom(content))


# ── table grid (shared with viewer) ───────────────────────────


def iter_table_rows(cells: list[dict], row_count: int, col_count: int):
    """Yield ``(row_idx, [(col_idx, cell_or_None), ...])`` for a styled table.

    Cells covered by a colspan/rowspan are skipped; grid positions with no cell
    yield ``(col_idx, None)``. Shared by the viewer and the dialect serializer
    so the grid-placement logic lives in one place.
    """
    grid: dict[tuple[int, int], dict] = {}
    covered: set[tuple[int, int]] = set()
    for cell in cells:
        r, c = cell.get("row", 0), cell.get("col", 0)
        grid[(r, c)] = cell
        rs, cs = cell.get("rowspan", 1), cell.get("colspan", 1)
        for dr in range(rs):
            for dc in range(cs):
                if dr or dc:
                    covered.add((r + dr, c + dc))
    for r in range(row_count):
        row: list[tuple[int, dict | None]] = []
        for c in range(col_count):
            if (r, c) in covered:
                continue
            row.append((c, grid.get((r, c))))
        yield r, row


# ── serialize ─────────────────────────────────────────────────


def _serialize_styled_table(meta: dict) -> str:
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


def _serialize_simple_table(meta: dict) -> str:
    headers = meta.get("headers", [])
    rows = meta.get("rows", [])
    thead = "<tr>" + "".join(f"<th>{escape(h)}</th>" for h in headers) + "</tr>"
    tbody = "".join(
        "<tr>" + "".join(f"<td>{escape(cell)}</td>" for cell in row) + "</tr>"
        for row in rows
    )
    return f"<table><thead>{thead}</thead><tbody>{tbody}</tbody></table>"


def _serialize_block(block: Block) -> str:
    t = block.type
    m = block.meta

    if t == BlockType.HEADING:
        level = max(1, min(6, int(m.get("level", 1))))
        return f"<h{level}>{_serialize_inline(block.content)}</h{level}>"

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
            return f'<pre><code class="language-{escape(lang, quote=True)}">{body}</code></pre>'
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
        src = _sanitize_url(m.get("src", ""))
        alt = m.get("alt", "")
        return f'<img src="{escape(src, quote=True)}" alt="{escape(alt, quote=True)}">'

    if t == BlockType.TABLE:
        if m.get("cells"):
            return _serialize_styled_table(m)
        return _serialize_simple_table(m)

    return f"<p>{_serialize_inline(block.content)}</p>"


def serialize_doc(doc: UniversalDoc) -> str:
    """Serialize a UniversalDoc to dialect HTML (pages flattened)."""
    parts: list[str] = [_ARTICLE_OPEN]
    for page in doc.pages:
        for block in page.blocks:
            parts.append(_serialize_block(block))
    parts.append(_ARTICLE_CLOSE)
    return "".join(parts)


# ── parse ─────────────────────────────────────────────────────


def _parse_pre(pre: _Node) -> Block:
    code = _first_child(pre, "code")
    target = code if code is not None else pre
    lang = ""
    if code is not None:
        cls = code.attrs.get("class", "")
        if cls.startswith("language-"):
            lang = cls[len("language-"):]
    meta = {"language": lang} if lang else {}
    return Block(type=BlockType.CODE, content=_text_content(target), meta=meta)


def _parse_styled_table(node: _Node) -> Block:
    rows_tr = [c for c in node.children if c.tag == "tr"]
    occupied: set[tuple[int, int]] = set()
    cells: list[dict] = []
    col_count = 0
    for r, tr in enumerate(rows_tr):
        c = 0
        for td in tr.children:
            if td.tag not in ("td", "th"):
                continue
            while (r, c) in occupied:
                c += 1
            colspan = _int_attr(td.attrs.get("colspan"), 1)
            rowspan = _int_attr(td.attrs.get("rowspan"), 1)
            style = css_to_style(td.attrs.get("style", ""))
            cell: dict = {
                "text": _text_content(td),
                "row": r,
                "col": c,
                "colspan": colspan,
                "rowspan": rowspan,
            }
            if style:
                cell["style"] = style
            cells.append(cell)
            for dr in range(rowspan):
                for dc in range(colspan):
                    if dr or dc:
                        occupied.add((r + dr, c + dc))
            col_count = max(col_count, c + colspan)
            c += colspan
    meta = {"cells": cells, "col_count": col_count, "row_count": len(rows_tr)}
    return Block(type=BlockType.TABLE, content="", meta=meta)


def _parse_table(node: _Node) -> Block:
    thead = _first_child(node, "thead")
    if thead is not None:
        header_tr = _first_child(thead, "tr")
        headers = (
            [_text_content(th) for th in header_tr.children if th.tag == "th"]
            if header_tr is not None
            else []
        )
        tbody = _first_child(node, "tbody")
        rows: list[list[str]] = []
        if tbody is not None:
            for tr in tbody.children:
                if tr.tag == "tr":
                    rows.append([_text_content(td) for td in tr.children if td.tag == "td"])
        return Block(type=BlockType.TABLE, content="", meta={"headers": headers, "rows": rows})
    return _parse_styled_table(node)


def _int_attr(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _blocks_from_children(nodes: list[_Node]) -> list[Block]:
    blocks: list[Block] = []
    for n in nodes:
        if n.tag is None:
            if n.text.strip():
                blocks.append(
                    Block(type=BlockType.PARAGRAPH, content=escape(n.text.strip()), meta={})
                )
        elif n.tag in _DROP_CONTENT:
            continue
        elif n.tag in _HEADING_TAGS:
            level = int(n.tag[1])
            blocks.append(
                Block(
                    type=BlockType.HEADING,
                    content=_render_inline(n.children),
                    meta={"level": level},
                )
            )
        elif n.tag == "p":
            style = css_to_style(n.attrs.get("style", ""))
            meta = {"style": style} if style else {}
            blocks.append(
                Block(type=BlockType.PARAGRAPH, content=_render_inline(n.children), meta=meta)
            )
        elif n.tag == "pre":
            blocks.append(_parse_pre(n))
        elif n.tag == "blockquote":
            blocks.append(Block(type=BlockType.QUOTE, content=_render_inline(n.children), meta={}))
        elif n.tag in ("ul", "ol"):
            items = [_render_inline(li.children) for li in n.children if li.tag == "li"]
            blocks.append(
                Block(
                    type=BlockType.LIST,
                    content="\n".join(items),
                    meta={"ordered": n.tag == "ol"},
                )
            )
        elif n.tag == "img":
            meta = {"src": _sanitize_url(n.attrs.get("src", "")), "alt": n.attrs.get("alt", "")}
            blocks.append(Block(type=BlockType.IMAGE, content="", meta=meta))
        elif n.tag == "table":
            blocks.append(_parse_table(n))
        elif _INLINE_ALIASES.get(n.tag, n.tag) in _INLINE_TAGS:
            inner = _render_inline([n])  # b/i → strong/em 매핑은 _render_inline 이 처리
            if inner:
                blocks.append(Block(type=BlockType.PARAGRAPH, content=inner, meta={}))
        else:
            # unknown block-level tag: unwrap, keeping recognized descendants
            blocks.extend(_blocks_from_children(n.children))
    return blocks


def parse_dialect(html: str) -> UniversalDoc:
    """Parse dialect HTML into a UniversalDoc (single page, or empty)."""
    dom = _build_dom(html)
    article = None
    for node in dom:
        if node.tag == "article":
            article = node
            break
    children = article.children if article is not None else dom
    blocks = _blocks_from_children(children)
    if not blocks:
        return UniversalDoc(pages=[])
    return UniversalDoc(pages=[Page(blocks=blocks)])
