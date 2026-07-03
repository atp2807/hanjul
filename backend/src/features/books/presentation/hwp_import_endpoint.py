"""HWP(한글) 원고 가져오기 — 상태 없는 파싱 전용 유틸리티.

DOCX/EPUB 가져오기는 브라우저에서 처리하지만 HWP/HWPX 는 바이너리 파싱이 필요해
서버를 거친다. 이 엔드포인트는 **책과 무관** — 파일 업로드 → 중립 블록 JSON 반환,
DB 저장은 전혀 하지 않는다(저장은 이후 기존 발행/동기화 흐름을 탐). 무단 남용을 막기
위해 로그인은 필수지만 소유권 체크는 없다(대상 책이 없음).

응답: `{"blocks": [...]}` — `hwp_to_neutral_blocks` 산출 형식 그대로, 프론트가 DOCX
가져오기와 동일 경로로 소비.
"""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from src.engine.imports.hwp_import import hwp_to_neutral_blocks
from src.features.auth.domain.models import AccountPrincipal
from src.features.auth.presentation.dependencies import get_current_account
from src.shared.errors import ValidationError

router = APIRouter(tags=["import"])

_MAX_BYTES = 20 * 1024 * 1024  # 20MB — 남용/메모리 방어


@router.post("/import/hwp-parse")
async def parse_hwp(
    file: UploadFile = File(...),
    _principal: AccountPrincipal = Depends(get_current_account),  # 로그인 필수 (남용 방지)
) -> dict:
    """HWP/HWPX 업로드 → 중립 블록 JSON. 손상/미지원 파일은 InvalidHwpFile → 422,
    이 서버 환경에서 rhwp 를 못 쓰면(네이티브 확장 로드 실패 등) 503."""
    data = await file.read()
    if len(data) > _MAX_BYTES:
        raise ValidationError("파일이 너무 커요 (20MB 이하).")
    try:
        blocks = hwp_to_neutral_blocks(data)
    except RuntimeError:
        raise HTTPException(503, "HWP 가져오기가 지금은 불가해요. 잠시 후 다시 시도해 주세요.")
    return {"blocks": blocks}
