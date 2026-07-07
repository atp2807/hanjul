from __future__ import annotations

from src.engine.doc.models import Block, BlockType, Page, UniversalDoc


class TextParser:
    """Parse plain text into UniversalDoc. Splits paragraphs by blank lines."""

    def parse(self, content: str) -> UniversalDoc:
        blocks = self._split_paragraphs(content)
        if not blocks:
            return UniversalDoc()
        return UniversalDoc(pages=[Page(blocks=blocks)])

    def _split_paragraphs(self, content: str) -> list[Block]:
        blocks: list[Block] = []
        current_lines: list[str] = []

        for line in content.split("\n"):
            if line.strip():
                current_lines.append(line)
            else:
                if current_lines:
                    blocks.append(Block(
                        type=BlockType.PARAGRAPH,
                        content="\n".join(current_lines),
                    ))
                    current_lines = []

        if current_lines:
            blocks.append(Block(
                type=BlockType.PARAGRAPH,
                content="\n".join(current_lines),
            ))

        return blocks
