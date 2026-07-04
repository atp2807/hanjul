"""HWP/HWPX 원고 가져오기 — 업로드 바이트 → 중립 doc 블록 리스트.

프론트 `web/src/writer/adapters/docx_import.js`(및 epub)가 만드는 중립 doc 과 완전히
동일한 형식을 낸다: {"type": "p", "spans": [{"text": str, "marks": []}]}.

이 라이브러리(hwp-hwpx-parser)는 순수 파이썬(olefile+lxml+python-docx)이라 네이티브
확장이 없어 CI(x86_64)/prod(aarch64) 아키텍처 결함을 원천 차단한다(이전 rhwp-python
undefined symbol 롤백 대체). 서식(굵게/기울임/헤딩)은 노출하지 않으므로 모든 문단은
marks=[] 의 "p" 로만 낸다.

의존성은 지연 임포트(함수 내부) — 임포트 실패는 RuntimeError 로 감싸 표현층 503,
파싱 실패는 InvalidHwpFile(422)로 감싸 사용자에게 PDF 변환 대안을 안내한다.
"""
import contextlib
import os
import tempfile

from src.shared.errors import ValidationError


class InvalidHwpFile(ValidationError):
    """HWP/HWPX 파싱 실패 — 손상 파일·미지원 옛 버전 등. 대안(PDF)까지 안내."""
    default_detail = "HWP 파일을 읽을 수 없어요. PDF로 변환한 후 다시 업로드해보세요."


def _ext_of(filename: str) -> str:
    """업로드 원본 파일명의 확장자(.hwp/.hwpx). 없으면 .hwpx 로 가정."""
    _, ext = os.path.splitext(filename or "")
    ext = ext.lower()
    return ext if ext in (".hwp", ".hwpx") else ".hwpx"


def hwp_to_neutral_blocks(data: bytes, filename: str) -> list[dict]:
    """업로드된 HWP/HWPX 바이트 → 중립 doc 블록 리스트.

    Reader 는 파일 경로만 받으므로(바이트 직접 불가) 임시파일에 원본 확장자로 써서 넘긴다.
    r.text 를 line_separator(기본 "\\n") 로 split 하면 원본 문단 경계가 복원된다
    (문서의 "paragraph_separator" 는 섹션 구분자라 오해 주의 — 기본값 그대로 사용).
    """
    try:
        from hwp_hwpx_parser import Reader
    except Exception as exc:  # 임포트 실패(환경/설치 문제) → 표현층 503
        raise RuntimeError("hwp-hwpx-parser import failed") from exc

    path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=_ext_of(filename), delete=False) as tmp:
            tmp.write(data)
            path = tmp.name
        try:
            with Reader(path) as reader:
                text = reader.text
        except Exception as exc:  # 손상/미지원 파일 등 라이브러리 예외 → 사용자 안내
            raise InvalidHwpFile() from exc
    finally:
        if path is not None:
            with contextlib.suppress(OSError):
                os.unlink(path)

    blocks: list[dict] = []
    for line in text.split("\n"):
        if line == "":
            continue  # 빈 문자열 문단은 버림
        blocks.append({"type": "p", "spans": [{"text": line, "marks": []}]})
    return blocks
