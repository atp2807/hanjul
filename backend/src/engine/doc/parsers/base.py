from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.engine.doc.models import UniversalDoc


@runtime_checkable
class Parser(Protocol):
    def parse(self, content: str) -> UniversalDoc: ...


@runtime_checkable
class BinaryParser(Protocol):
    def parse_bytes(self, content: bytes) -> UniversalDoc: ...
