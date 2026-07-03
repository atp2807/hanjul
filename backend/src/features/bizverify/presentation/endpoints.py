"""bizverify API — 사업자등록번호 진위확인 (인증 필요)."""
from fastapi import APIRouter, Depends, HTTPException, Query

from src.features.auth.domain.models import AccountPrincipal
from src.features.auth.presentation.dependencies import get_current_account
from src.features.bizverify.application.bizverify_service import BizVerifyService
from src.features.bizverify.presentation.dependencies import get_bizverify_service
from src.features.bizverify.presentation.schemas import BusinessRegistrationResponse

router = APIRouter(prefix="/business-number", tags=["bizverify"])


@router.get("/verify", response_model=BusinessRegistrationResponse)
async def verify_business_number(
    business_no: str = Query(..., alias="businessNo"),
    _principal: AccountPrincipal = Depends(get_current_account),
    service: BizVerifyService = Depends(get_bizverify_service),
) -> BusinessRegistrationResponse:
    """체크섬 검증 후 국세청 조회. 형식오류 422·미등록 404·외부실패 502(중앙 핸들러)."""
    try:
        result = await service.verify(business_no)
    except RuntimeError:
        raise HTTPException(503, "사업자 조회가 지금은 불가해요. 잠시 후 다시 시도해 주세요.")
    return BusinessRegistrationResponse.model_validate(result)
