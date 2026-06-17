"""입력 텍스트(TXT/Markdown-lite) → 정본 HTML 블록 변환 (순수 함수).

engine 레이어 = stdlib만. DB·프레임워크 의존 없음 → 단위 테스트가 쉽다.
출력은 persistence-agnostic 한 dict 리스트: {"type": <블록종류>, "html": <HTML 조각>}.

지원 문법(MVP):
  # / ## / ###   → H1 / H2 / H3
  > 인용          → QUOTE (blockquote)
  --- / *** / ___ → HR
  빈 줄로 구분된 그 외 텍스트 → P (문단)
인라인 서식(**굵게** 등)은 아직 미지원 — 텍스트는 HTML escape 만 적용.
"""
import html as _html

# 블록 종류 상수 (DB block_type_cd 와 1:1)
P, H1, H2, H3, QUOTE, HR = "P", "H1", "H2", "H3", "QUOTE", "HR"

# 긴 prefix 우선 (### 를 # 보다 먼저)
_HEADINGS = [("### ", H3), ("## ", H2), ("# ", H1)]
_HR_TOKENS = {"---", "***", "___"}


def _escape(text: str) -> str:
    return _html.escape(text, quote=False)


def text_to_blocks(raw: str) -> list[dict]:
    """raw 텍스트를 정본 HTML 블록 리스트로 변환한다."""
    if not raw:
        return []

    lines = raw.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    blocks: list[dict] = []
    para: list[str] = []

    def flush_para() -> None:
        if para:
            text = " ".join(s.strip() for s in para).strip()
            if text:
                blocks.append({"type": P, "html": f"<p>{_escape(text)}</p>"})
            para.clear()

    for line in lines:
        stripped = line.strip()

        if not stripped:
            flush_para()
            continue

        if stripped in _HR_TOKENS:
            flush_para()
            blocks.append({"type": HR, "html": "<hr/>"})
            continue

        heading = next(((pre, bt) for pre, bt in _HEADINGS if stripped.startswith(pre)), None)
        if heading:
            flush_para()
            prefix, btype = heading
            text = stripped[len(prefix):].strip()
            tag = btype.lower()
            blocks.append({"type": btype, "html": f"<{tag}>{_escape(text)}</{tag}>"})
            continue

        if stripped.startswith("> "):
            flush_para()
            text = stripped[2:].strip()
            blocks.append({"type": QUOTE, "html": f"<blockquote>{_escape(text)}</blockquote>"})
            continue

        para.append(line)

    flush_para()
    return blocks
