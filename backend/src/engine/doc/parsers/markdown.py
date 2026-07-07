from __future__ import annotations

import re

from src.engine.doc.models import Block, BlockType, Page, UniversalDoc


class MarkdownParser:
    """Parse standard Markdown into UniversalDoc."""

    def parse(self, content: str) -> UniversalDoc:
        lines = content.split("\n")
        blocks = self._parse_lines(lines)
        if not blocks:
            return UniversalDoc()
        return UniversalDoc(pages=[Page(blocks=blocks)])

    def _parse_lines(self, lines: list[str]) -> list[Block]:
        blocks: list[Block] = []
        i = 0
        while i < len(lines):
            line = lines[i]

            # Skip blank lines
            if not line.strip():
                i += 1
                continue

            # Fenced code block
            if line.startswith("```"):
                block, i = self._parse_code_block(lines, i)
                blocks.append(block)
                continue

            # Heading
            m = re.match(r"^(#{1,6})\s+(.*)", line)
            if m:
                level = len(m.group(1))
                blocks.append(Block(
                    type=BlockType.HEADING,
                    content=m.group(2).strip(),
                    meta={"level": level},
                ))
                i += 1
                continue

            # Image (standalone line)
            m = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", line)
            if m:
                blocks.append(Block(
                    type=BlockType.IMAGE,
                    content="",
                    meta={"alt": m.group(1), "src": m.group(2)},
                ))
                i += 1
                continue

            # Blockquote
            if line.startswith(">"):
                block, i = self._parse_quote(lines, i)
                blocks.append(block)
                continue

            # Table
            if "|" in line and i + 1 < len(lines) and re.match(r"^\|[\s\-:|]+\|", lines[i + 1]):
                block, i = self._parse_table(lines, i)
                blocks.append(block)
                continue

            # Unordered list
            if re.match(r"^[-*+]\s+", line):
                block, i = self._parse_list(lines, i, ordered=False)
                blocks.append(block)
                continue

            # Ordered list
            if re.match(r"^\d+\.\s+", line):
                block, i = self._parse_list(lines, i, ordered=True)
                blocks.append(block)
                continue

            # Paragraph (default)
            block, i = self._parse_paragraph(lines, i)
            blocks.append(block)

        return blocks

    def _parse_code_block(self, lines: list[str], start: int) -> tuple[Block, int]:
        opening = lines[start]
        language = opening[3:].strip()
        code_lines: list[str] = []
        i = start + 1
        while i < len(lines):
            if lines[i].startswith("```"):
                i += 1
                break
            code_lines.append(lines[i])
            i += 1
        return Block(
            type=BlockType.CODE,
            content="\n".join(code_lines),
            meta={"language": language},
        ), i

    def _parse_quote(self, lines: list[str], start: int) -> tuple[Block, int]:
        quote_lines: list[str] = []
        i = start
        while i < len(lines) and lines[i].startswith(">"):
            text = re.sub(r"^>\s?", "", lines[i])
            quote_lines.append(text)
            i += 1
        return Block(
            type=BlockType.QUOTE,
            content="\n".join(quote_lines),
        ), i

    def _parse_table(self, lines: list[str], start: int) -> tuple[Block, int]:
        header_cells = [c.strip() for c in lines[start].strip("|").split("|")]
        i = start + 2  # skip separator line
        rows: list[list[str]] = []
        while i < len(lines) and "|" in lines[i] and lines[i].strip():
            cells = [c.strip() for c in lines[i].strip("|").split("|")]
            rows.append(cells)
            i += 1
        return Block(
            type=BlockType.TABLE,
            content="",
            meta={"headers": header_cells, "rows": rows},
        ), i

    def _parse_list(
        self, lines: list[str], start: int, *, ordered: bool
    ) -> tuple[Block, int]:
        pattern = r"^\d+\.\s+(.*)" if ordered else r"^[-*+]\s+(.*)"
        items: list[str] = []
        i = start
        while i < len(lines) and (m := re.match(pattern, lines[i])):
            items.append(m.group(1))
            i += 1
        return Block(
            type=BlockType.LIST,
            content="\n".join(items),
            meta={"ordered": ordered},
        ), i

    def _parse_paragraph(self, lines: list[str], start: int) -> tuple[Block, int]:
        para_lines: list[str] = []
        i = start
        while i < len(lines) and lines[i].strip() and not self._is_block_start(lines[i]):
            para_lines.append(lines[i])
            i += 1
        return Block(
            type=BlockType.PARAGRAPH,
            content="\n".join(para_lines),
        ), i

    def _is_block_start(self, line: str) -> bool:
        if line.startswith(("```", "#", ">", "- ", "* ", "+ ")):
            return True
        if re.match(r"^\d+\.\s+", line):
            return True
        return bool(re.match(r"^!\[", line))
