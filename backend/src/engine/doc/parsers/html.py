"""HTML import parser — external HTML → UniversalDoc.

The heavy lifting (tolerant parsing + sanitization) is *not* reimplemented here:
:func:`juldoc.dialect.parse_dialect` already does idiomatic HTML parsing, drops
``script``/``style``/``iframe`` content, unwraps unknown tags, and whitelists
attributes. This module's only job is to turn *bytes of unknown encoding* into a
correct ``str`` and hand it to ``parse_dialect``.

Encoding decision order (first that succeeds wins):

1. BOM (UTF-8 / UTF-16 LE / UTF-16 BE),
2. a ``<meta charset=...>`` / ``Content-Type`` declaration in the head,
3. plain UTF-8,
4. CP949 fallback (Korean legacy pages, e.g. KEPCO secure mail).

Pure stdlib. Named ``html`` like the stdlib package, but Python 3 absolute
imports keep ``juldoc.parsers.html`` and the stdlib ``html`` distinct; this
module needs neither ``html`` nor ``html.parser`` (charset scan is a byte regex),
so there is no import collision.
"""
from __future__ import annotations

import re

from src.engine.doc.dialect import parse_dialect
from src.engine.doc.models import UniversalDoc

_BOM_UTF8 = b"\xef\xbb\xbf"
_BOM_UTF16_LE = b"\xff\xfe"
_BOM_UTF16_BE = b"\xfe\xff"

# Scan raw bytes (not yet decoded) for a charset declaration. Matches both
# `<meta charset="utf-8">` and `<meta http-equiv=... content="...; charset=euc-kr">`.
_CHARSET_RE = re.compile(rb"""charset\s*=\s*["']?\s*([a-zA-Z0-9_\-]+)""", re.IGNORECASE)
# The declaration lives in <head>; cap the scan there (or a generous prefix) so a
# stray "charset=" inside body script/text cannot hijack the decision.
_HEAD_END_RE = re.compile(rb"</head\s*>", re.IGNORECASE)
_HEAD_SCAN_LIMIT = 8192


def _meta_charset(content: bytes) -> str | None:
    """Return the declared charset name (lowercased) from the head, or None."""
    end = _HEAD_END_RE.search(content)
    scan = content[: end.start()] if end else content[:_HEAD_SCAN_LIMIT]
    m = _CHARSET_RE.search(scan)
    if m is None:
        return None
    return m.group(1).decode("ascii", "replace").lower()


def _decode_html(content: bytes) -> str:
    """Decode HTML bytes to str using the BOM → meta → utf-8 → cp949 ladder."""
    if content.startswith(_BOM_UTF8):
        return content.decode("utf-8-sig")
    if content.startswith((_BOM_UTF16_LE, _BOM_UTF16_BE)):
        return content.decode("utf-16")

    declared = _meta_charset(content)
    if declared and declared not in ("utf-8", "utf8"):
        try:
            return content.decode(declared)
        except (LookupError, UnicodeDecodeError):
            pass

    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("cp949", errors="replace")


class HTMLParser:
    """Parse external HTML bytes into a UniversalDoc (via the dialect pipeline)."""

    def parse_bytes(self, content: bytes) -> UniversalDoc:
        return parse_dialect(_decode_html(content))
