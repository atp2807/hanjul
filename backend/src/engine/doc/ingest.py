from __future__ import annotations

from pathlib import Path

from src.engine.doc.models import UniversalDoc
from src.engine.doc.parsers.base import BinaryParser, Parser
from src.engine.doc.parsers.csv import CSVParser
from src.engine.doc.parsers.docx import DOCXParser
from src.engine.doc.parsers.html import HTMLParser
from src.engine.doc.parsers.hwp import HWPParser
from src.engine.doc.parsers.hwpx import HWPXParser
from src.engine.doc.parsers.markdown import MarkdownParser
from src.engine.doc.parsers.pdf import PDFParser
from src.engine.doc.parsers.pptx import PPTXParser
from src.engine.doc.parsers.text import TextParser
from src.engine.doc.parsers.xlsx import XLSXParser

PARSER_REGISTRY: dict[str, Parser | BinaryParser] = {
    "md": MarkdownParser(),
    "txt": TextParser(),
    "hwp": HWPParser(),
    "hwpx": HWPXParser(),
    "docx": DOCXParser(),
    "pdf": PDFParser(),
    "html": HTMLParser(),
    "htm": HTMLParser(),
    "csv": CSVParser(),
    "pptx": PPTXParser(),
    "xlsx": XLSXParser(),
}

# 인코딩 판단이 필요한 텍스트 계열(html/csv)도 바이트로 받아 파서가 디코딩한다
BINARY_FORMATS: set[str] = {"hwp", "hwpx", "docx", "pdf", "html", "htm", "csv", "pptx", "xlsx"}


def detect_format(path: Path) -> str:
    """Extract lowercase extension without dot. Raises ValueError if unsupported."""
    suffix = path.suffix.lower().lstrip(".")
    if not suffix or suffix not in PARSER_REGISTRY:
        raise ValueError(f"Unsupported format: {suffix or path.name}")
    return suffix


def get_parser(format: str) -> Parser | BinaryParser:
    """Look up parser by format key. Raises ValueError if not found."""
    if format not in PARSER_REGISTRY:
        raise ValueError(f"Unsupported format: {format}")
    return PARSER_REGISTRY[format]


def ingest(file_path: Path) -> UniversalDoc:
    """Read file, detect format, parse, and inject metadata."""
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    fmt = detect_format(file_path)
    parser = get_parser(fmt)
    if fmt in BINARY_FORMATS:
        doc = parser.parse_bytes(file_path.read_bytes())  # type: ignore[union-attr]
    else:
        doc = parser.parse(file_path.read_text(encoding="utf-8"))  # type: ignore[union-attr]
    doc.metadata["source"] = str(file_path)
    doc.metadata["format"] = fmt
    return doc
