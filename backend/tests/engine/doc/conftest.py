from __future__ import annotations

import pytest


@pytest.fixture
def make_block():
    """Factory fixture to create Block instances."""
    from src.engine.doc.models import Block, BlockType

    def _make(
        block_type: BlockType = BlockType.PARAGRAPH,
        content: str = "hello",
        *,
        meta: dict | None = None,
    ) -> Block:
        return Block(type=block_type, content=content, meta=meta or {})

    return _make


@pytest.fixture
def make_page():
    """Factory fixture to create Page instances."""
    from src.engine.doc.models import Page

    def _make(blocks=None) -> Page:
        return Page(blocks=blocks or [])

    return _make


@pytest.fixture
def make_doc():
    """Factory fixture to create UniversalDoc instances."""
    from src.engine.doc.models import UniversalDoc

    def _make(pages=None, *, metadata=None) -> UniversalDoc:
        return UniversalDoc(pages=pages or [], metadata=metadata or {})

    return _make


@pytest.fixture
def sample_markdown() -> str:
    """Sample markdown document covering all block types."""
    return """\
# Main Title

This is a paragraph with **bold** and *italic* text.

## Subtitle

> This is a blockquote
> spanning multiple lines

```python
def hello():
    print("world")
```

- item one
- item two
- item three

1. first
2. second
3. third

| Name | Age |
|------|-----|
| Alice | 30 |
| Bob | 25 |

![alt text](image.png)

Another paragraph at the end.
"""


@pytest.fixture
def empty_markdown() -> str:
    return ""


@pytest.fixture
def heading_only_markdown() -> str:
    return "# Just a heading\n"


@pytest.fixture
def sample_text() -> str:
    """Sample plain text with multiple paragraphs."""
    return """\
This is the first paragraph.
It has multiple lines.

This is the second paragraph.

This is the third paragraph.
"""


@pytest.fixture
def empty_text() -> str:
    return ""
