"""HWP/HWPX 가져오기 API — 상태 없는 파싱 전용(book 과 무관).

업로드 파일을 중립 doc 블록으로 변환만 해 돌려준다(DB 저장 없음). 로그인만 필요
(소유권 체크 없음 — book_id 안 받음). 파싱 실패(422)는 도메인 예외가 중앙 핸들러로,
임포트 실패(설치/환경)는 RuntimeError → 503 으로 반드시 잡는다(놓치면 500 새 나감).
"""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from src.engine.imports.hwp_import import hwp_to_neutral_blocks
from src.features.auth.domain.models import AccountPrincipal
from src.features.auth.presentation.dependencies import get_current_account

router = APIRouter(tags=["imports"])

_MAX_BYTES = 20 * 1024 * 1024  # 20MB


@router.post("/import/hwp-parse")
async def parse_hwp(
    file: UploadFile = File(...),
    _principal: AccountPrincipal = Depends(get_current_account),
) -> dict:
    """HWP/HWPX 업로드 → 중립 doc {blocks}. 손상 파일 422(PDF 변환 안내)·환경 실패 503."""
    data = await file.read()
    if len(data) > _MAX_BYTES:
        raise HTTPException(413, "원고 파일은 20MB 이하여야 해요")
    try:
        blocks = hwp_to_neutral_blocks(data, file.filename or "")
    except RuntimeError:
        raise HTTPException(503, "HWP 가져오기가 지금은 불가해요. 잠시 후 다시 시도해 주세요.")
    return {"blocks": blocks}
