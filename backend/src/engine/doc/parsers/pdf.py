"""PDF parser — converts PDF documents to UniversalDoc.

Uses pdfminer.six (BSD/MIT-style license) for layout analysis.  pymupdf is
deliberately avoided because it is AGPL-licensed.

v1 scope: page-by-page text extraction into PARAGRAPH blocks, a font-size
heuristic for HEADING inference, image-name collection, and page dimensions.
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from statistics import median

from pdfminer.high_level import extract_pages
from pdfminer.layout import (
    LAParams,
    LTChar,
    LTContainer,
    LTImage,
    LTTextContainer,
    LTTextLine,
)
from pdfminer.pdfdocument import (
    PDFDocument,
    PDFEncryptionError,
    PDFPasswordIncorrect,
)
from pdfminer.pdfparser import PDFParser as _PDFMinerParser
from pdfminer.pdfparser import PDFSyntaxError
from pdfminer.psparser import PSException

from src.engine.doc.models import Block, BlockType, Page, UniversalDoc

# Font-size ratio at/above which a single-line block is treated as a heading.
_HEADING_RATIO = 1.3
# Maximum heading level emitted (levels are 1..3).
_MAX_HEADING_LEVEL = 3


# ---------------------------------------------------------------------------
# Internal data types
# ---------------------------------------------------------------------------
@dataclass
class _RawBlock:
    """A text container reduced to the fields the heuristics care about."""

    text: str
    size: float          # representative (median) font size in pt
    line_count: int      # number of visual text lines


# ---------------------------------------------------------------------------
# Low-level extraction helpers
# ---------------------------------------------------------------------------

def _iter_chars(element: object) -> list[LTChar]:
    """Recursively collect LTChar leaves under a layout element."""
    chars: list[LTChar] = []
    if isinstance(element, LTChar):
        chars.append(element)
    elif isinstance(element, LTContainer):
        for child in element:
            chars.extend(_iter_chars(child))
    return chars


def _block_font_size(container: LTTextContainer) -> float:
    """Representative font size of a text container: median of its char sizes."""
    sizes = [round(ch.size, 1) for ch in _iter_chars(container)]
    if not sizes:
        return 0.0
    return round(median(sizes), 1)


def _count_lines(container: LTTextContainer) -> int:
    """Number of visual text lines in a container (min 1 for non-empty text)."""
    lines = sum(1 for child in container if isinstance(child, LTTextLine))
    return max(lines, 1)


def _collect_images(element: object) -> list[str]:
    """Recursively collect image names (LTImage.name) under a layout element."""
    names: list[str] = []
    if isinstance(element, LTImage):
        if element.name:
            names.append(element.name)
    elif isinstance(element, LTContainer):
        for child in element:
            names.extend(_collect_images(child))
    return names


# ---------------------------------------------------------------------------
# Heading heuristic (pure — unit-tested with synthetic data)
# ---------------------------------------------------------------------------

def infer_heading_levels(
    sizes: list[float],
    line_counts: list[int],
    *,
    ratio: float = _HEADING_RATIO,
) -> list[int | None]:
    """Classify text blocks as headings by relative font size.

    A block is a heading when it is a single visual line *and* its font size is
    at least *ratio* times the page's median block font size.  Qualifying blocks
    receive a level in 1..3 assigned by descending distinct size (largest size ->
    level 1).  Non-heading blocks map to ``None``.

    Returns a list aligned with the inputs.
    """
    n = len(sizes)
    if n == 0 or len(line_counts) != n:
        return [None] * n

    positive = [s for s in sizes if s > 0]
    if not positive:
        return [None] * n

    threshold = median(positive) * ratio

    def qualifies(i: int) -> bool:
        return sizes[i] > 0 and line_counts[i] == 1 and sizes[i] >= threshold

    heading_sizes = sorted(
        {round(sizes[i], 1) for i in range(n) if qualifies(i)},
        reverse=True,
    )
    rank = {size: idx for idx, size in enumerate(heading_sizes)}

    levels: list[int | None] = []
    for i in range(n):
        if qualifies(i):
            level = min(rank[round(sizes[i], 1)] + 1, _MAX_HEADING_LEVEL)
            levels.append(level)
        else:
            levels.append(None)
    return levels


def _raw_blocks_to_page(raw_blocks: list[_RawBlock]) -> Page:
    """Convert reduced text blocks into a Page, tagging headings by font size."""
    levels = infer_heading_levels(
        [b.size for b in raw_blocks],
        [b.line_count for b in raw_blocks],
    )
    blocks: list[Block] = []
    for raw, level in zip(raw_blocks, levels, strict=False):
        if level is not None:
            blocks.append(
                Block(type=BlockType.HEADING, content=raw.text, meta={"level": level})
            )
        else:
            blocks.append(Block(type=BlockType.PARAGRAPH, content=raw.text))
    return Page(blocks=blocks)


# ---------------------------------------------------------------------------
# Encryption guard
# ---------------------------------------------------------------------------

def _reject_if_encrypted(content: bytes) -> None:
    """Raise ValueError if the PDF is encrypted (matches HWP parser tone)."""
    try:
        document = PDFDocument(_PDFMinerParser(io.BytesIO(content)))
    except (PDFPasswordIncorrect, PDFEncryptionError) as exc:
        raise ValueError("encrypted PDF not supported") from exc
    except PDFSyntaxError as exc:
        raise ValueError("invalid PDF") from exc
    if document.encryption is not None:
        raise ValueError("encrypted PDF not supported")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class PDFParser:
    """Parse PDF binary files into UniversalDoc."""

    def parse_bytes(self, content: bytes) -> UniversalDoc:
        _reject_if_encrypted(content)

        pages: list[Page] = []
        images: list[str] = []
        page_layout: dict | None = None

        # pdfminer defers most structural validation to layout analysis, so a
        # malformed/truncated PDF surfaces as a PSException (base of PDFException
        # /PDFSyntaxError) while iterating. Map the whole family to ValueError.
        try:
            for page_layout_obj in extract_pages(io.BytesIO(content), laparams=LAParams()):
                if page_layout is None:
                    page_layout = {
                        "width_pt": round(float(page_layout_obj.width), 2),
                        "height_pt": round(float(page_layout_obj.height), 2),
                    }

                raw_blocks: list[_RawBlock] = []
                for element in page_layout_obj:
                    if isinstance(element, LTTextContainer):
                        text = element.get_text().strip()
                        if text:
                            raw_blocks.append(
                                _RawBlock(
                                    text=text,
                                    size=_block_font_size(element),
                                    line_count=_count_lines(element),
                                )
                            )
                    images.extend(_collect_images(element))

                pages.append(_raw_blocks_to_page(raw_blocks))
        except PSException as exc:
            raise ValueError("invalid PDF") from exc

        metadata: dict = {}
        if images:
            metadata["images"] = images
        if page_layout is not None:
            metadata["page_layout"] = page_layout

        return UniversalDoc(pages=pages, metadata=metadata)
