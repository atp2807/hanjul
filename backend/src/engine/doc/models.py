from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class BlockType(StrEnum):
    HEADING = "HEADING"
    PARAGRAPH = "PARAGRAPH"
    CODE = "CODE"
    IMAGE = "IMAGE"
    QUOTE = "QUOTE"
    LIST = "LIST"
    TABLE = "TABLE"


@dataclass
class Block:
    type: BlockType
    content: str
    meta: dict = field(default_factory=dict)


@dataclass
class Page:
    blocks: list[Block] = field(default_factory=list)


@dataclass
class UniversalDoc:
    pages: list[Page] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
