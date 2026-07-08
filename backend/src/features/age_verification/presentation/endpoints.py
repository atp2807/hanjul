"""age-verification 고객 API — 성인인증(AGE18) 신청 + 진행상태 조회.

신분증 사진은 PII — 이 라우터는 업로드만 받고 바로 비공개 저장소로 보낸다. 조회는 본인
현재 진행중(PENDING) 요청뿐(사진 자체는 potato 운영자 전용 엔드포인트로만 열람 가능).
"""
from fastapi import APIRouter, Depends, File, UploadFile

from src.features.age_verification.application.age_verification_service import (
    AgeVerificationService,
)
from src.features.age_verification.domain.models import InvalidImageFile
from src.features.age_verification.presentation.dependencies import get_age_verification_service
from src.features.age_verification.presentation.schemas import AgeVerificationRequestResponse
from src.features.auth.domain.models import AccountPrincipal
from src.features.auth.presentation.dependencies import get_current_account

router = APIRouter(prefix="/me/age-verification", tags=["age-verification"])

_IMAGE_EXT = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}
_MAX_BYTES = 5 * 1024 * 1024  # 5MB


@router.post("", response_model=AgeVerificationRequestResponse, status_code=201)
async def submit(
    file: UploadFile = File(...),
    principal: AccountPrincipal = Depends(get_current_account),
    svc: AgeVerificationService = Depends(get_age_verification_service),
) -> AgeVerificationRequestResponse:
    """신분증 사진 업로드 → 성인인증 심사 요청. AlreadyPending(409) → 중앙 핸들러."""
    ext = _IMAGE_EXT.get(file.content_type)
    if ext is None:
        raise InvalidImageFile()
    data = await file.read()
    if len(data) > _MAX_BYTES:
        raise InvalidImageFile("신분증 이미지는 5MB 이하여야 해요.")
    req = await svc.submit(principal.id, data, ext)
    return AgeVerificationRequestResponse.model_validate(req)


@router.get("", response_model=AgeVerificationRequestResponse | None)
async def my_status(
    principal: AccountPrincipal = Depends(get_current_account),
    svc: AgeVerificationService = Depends(get_age_verification_service),
) -> AgeVerificationRequestResponse | None:
    """현재 진행중(PENDING) 인증 요청 — 없으면 null(과거 승인/거부 이력은 노출 안 함)."""
    req = await svc.my_request(principal.id)
    return AgeVerificationRequestResponse.model_validate(req) if req else None
