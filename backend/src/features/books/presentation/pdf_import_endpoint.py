"""PDF 원고 가져오기 API — 상태 없는 파싱 전용 (book 무관, HWP 엔드포인트와 대칭).

업로드된 PDF 를 그 자리에서 중립 doc 블록으로 파싱해 돌려줄 뿐 DB 저장은 없다.
프론트가 결과를 에디터에 적재하고, 저장/출판은 기존 content 경로로 간다.

RuntimeError(pymupdf 미설치·로드 실패) → 503. 손상 파일은 파서가 InvalidPdfFile(422)로.
"""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from src.engine.imports.pdf_import import pdf_to_neutral_blocks
from src.features.auth.domain.models import AccountPrincipal
from src.features.auth.presentation.dependencies import get_current_account
from src.shared.errors import ValidationError

router = APIRouter(tags=["imports"])

_MAX_BYTES = 20 * 1024 * 1024  # 20MB


@router.post("/import/pdf-parse")
async def parse_pdf(
    file: UploadFile = File(...),
    _principal: AccountPrincipal = Depends(get_current_account),  # 로그인 필수
) -> dict:
    """PDF 업로드 → 중립 doc 블록 JSON (저장 없음)."""
    data = await file.read()
    if len(data) > _MAX_BYTES:
        raise ValidationError("PDF 는 20MB 이하여야 해요")
    try:
        blocks = pdf_to_neutral_blocks(data)
    except RuntimeError:
        raise HTTPException(503, "PDF 가져오기가 지금은 불가해요. 잠시 후 다시 시도해 주세요.")
    return {"blocks": blocks}
