from __future__ import annotations

from html import escape

from src.engine.doc.dialect import iter_table_rows, style_to_css
from src.engine.doc.models import Block, BlockType, UniversalDoc

# The abstract-style-dict -> CSS codec lives in dialect (which owns the
# serialization contract); the viewer only consumes it for display rendering.
_style_attr = style_to_css


def render_block(block: Block) -> str:
    """Render a single Block to an HTML string."""
    t = block.type
    c = escape(block.content)
    m = block.meta

    if t == BlockType.HEADING:
        level = m.get("level", 1)
        return f"<h{level}>{c}</h{level}>"

    if t == BlockType.PARAGRAPH:
        style = m.get("style", {})
        if style:
            css = _style_attr(style)
            return f'<p style="{css}">{c}</p>'
        return f"<p>{c}</p>"

    if t == BlockType.CODE:
        lang = m.get("language", "")
        if lang:
            return f'<pre><code class="language-{escape(lang)}">{c}</code></pre>'
        return f"<pre><code>{c}</code></pre>"

    if t == BlockType.IMAGE:
        src = escape(m.get("src", ""), quote=True).replace("=", "&#61;")
        alt = escape(m.get("alt", ""), quote=True).replace("=", "&#61;")
        return f'<img src="{src}" alt="{alt}">'

    if t == BlockType.QUOTE:
        return f"<blockquote>{c}</blockquote>"

    if t == BlockType.LIST:
        ordered = m.get("ordered", False)
        tag = "ol" if ordered else "ul"
        items = "".join(f"<li>{escape(item)}</li>" for item in block.content.split("\n") if item)
        return f"<{tag}>{items}</{tag}>"

    if t == BlockType.TABLE:
        cells = m.get("cells")
        if cells:
            return _render_styled_table(m)
        headers = m.get("headers", [])
        rows = m.get("rows", [])
        thead = "<tr>" + "".join(f"<th>{escape(h)}</th>" for h in headers) + "</tr>"
        tbody = "".join(
            "<tr>" + "".join(f"<td>{escape(cell)}</td>" for cell in row) + "</tr>"
            for row in rows
        )
        return f"<table><thead>{thead}</thead><tbody>{tbody}</tbody></table>"

    return f"<p>{c}</p>"


def _render_styled_table(meta: dict) -> str:
    """Render a table with cell structure (colspan, rowspan, widths, styles)."""
    cells = meta["cells"]
    col_count = meta.get("col_count", 1)
    row_count = meta.get("row_count", 1)

    # Grid placement (colspan/rowspan) is shared with the dialect serializer.
    html_rows: list[str] = []
    for _row_idx, row in iter_table_rows(cells, row_count, col_count):
        tds: list[str] = []
        for _col_idx, cell in row:
            if cell is None:
                tds.append("<td></td>")
                continue
            text = escape(cell.get("text", ""))
            attrs: list[str] = []
            cs = cell.get("colspan", 1)
            rs = cell.get("rowspan", 1)
            if cs > 1:
                attrs.append(f'colspan="{cs}"')
            if rs > 1:
                attrs.append(f'rowspan="{rs}"')
            style_parts: list[str] = []
            if "width_mm" in cell:
                style_parts.append(f'width:{cell["width_mm"]}mm')
            if "height_mm" in cell:
                style_parts.append(f'height:{cell["height_mm"]}mm')
            cell_style = cell.get("style", {})
            if cell_style:
                style_parts.append(_style_attr(cell_style))
            if style_parts:
                attrs.append(f'style="{"; ".join(style_parts)}"')
            attr_str = (" " + " ".join(attrs)) if attrs else ""
            tds.append(f"<td{attr_str}>{text}</td>")
        html_rows.append("<tr>" + "".join(tds) + "</tr>")

    return "<table>" + "".join(html_rows) + "</table>"


def render_doc(doc: UniversalDoc) -> str:
    """Render a full UniversalDoc to an HTML string."""
    parts: list[str] = []
    for page in doc.pages:
        for block in page.blocks:
            parts.append(render_block(block))
    return "\n".join(parts)
