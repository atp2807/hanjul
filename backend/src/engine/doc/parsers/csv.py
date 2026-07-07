"""CSV import parser — CSV bytes → UniversalDoc with a single TABLE block.

The whole CSV becomes one ``Page`` holding one ``TABLE`` block whose ``meta`` is
``{"headers": <first row>, "rows": <remaining rows>}`` — the exact shape the
Markdown table parser emits and the dialect serializer / viewer render, so no
viewer change is needed.

Encoding: UTF-8 (BOM-tolerant) first, CP949 fallback (Korean government exports,
e.g. the MOLIT legal-dong code file). Delimiter: :class:`csv.Sniffer` on a small
sample, comma on failure. An empty input yields an empty ``UniversalDoc()``.

Named ``csv`` like the stdlib module, but Python 3 absolute imports keep
``juldoc.parsers.csv`` and the stdlib ``csv`` distinct — ``import csv`` below
still binds the standard library.
"""
from __future__ import annotations

import csv
import io

from src.engine.doc.models import Block, BlockType, Page, UniversalDoc

# Sniff/decode on a bounded prefix so multi-MB files (49k+ rows) stay cheap.
_SNIFF_SAMPLE = 16384
_SNIFF_DELIMITERS = ",\t;|"


def _decode_csv(content: bytes) -> str:
    """Decode CSV bytes: UTF-8 (BOM-stripping) first, CP949 fallback."""
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return content.decode("cp949", errors="replace")


def _detect_delimiter(sample: str) -> str:
    try:
        return csv.Sniffer().sniff(sample, delimiters=_SNIFF_DELIMITERS).delimiter
    except csv.Error:
        return ","


class CSVParser:
    """Parse CSV bytes into a UniversalDoc: one Page, one TABLE block."""

    def parse_bytes(self, content: bytes) -> UniversalDoc:
        if not content.strip():
            return UniversalDoc()

        text = _decode_csv(content)
        delimiter = _detect_delimiter(text[:_SNIFF_SAMPLE])

        # StringIO is a file object, so csv.reader correctly re-joins quoted
        # fields that span multiple physical lines.
        reader = csv.reader(io.StringIO(text), delimiter=delimiter)
        rows = [row for row in reader if row]
        if not rows:
            return UniversalDoc()

        block = Block(
            type=BlockType.TABLE,
            content="",
            meta={"headers": rows[0], "rows": rows[1:]},
        )
        return UniversalDoc(pages=[Page(blocks=[block])])
