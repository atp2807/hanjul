"""payouts API — 작가 출금계좌 + 출금 신청/내역."""
from fastapi import APIRouter, Depends

from src.features.auth.domain.models import AccountPrincipal
from src.features.auth.presentation.dependencies import get_current_account
from src.features.payouts.application.payout_service import PayoutService
from src.features.payouts.presentation.dependencies import get_payout_service
from src.features.payouts.presentation.schemas import (
    BankAccountRequest,
    BankAccountResponse,
    PayableResponse,
    PayoutResponse,
)

router = APIRouter(tags=["payouts"])


@router.get("/me/bank-account", response_model=BankAccountResponse | None)
async def my_bank_account(
    principal: AccountPrincipal = Depends(get_current_account),
    svc: PayoutService = Depends(get_payout_service),
):
    acc = await svc.get_bank_account(principal.id)
    return BankAccountResponse.model_validate(acc) if acc else None


@router.put("/me/bank-account", response_model=BankAccountResponse)
async def set_bank_account(
    body: BankAccountRequest,
    principal: AccountPrincipal = Depends(get_current_account),
    svc: PayoutService = Depends(get_payout_service),
) -> BankAccountResponse:
    # 입력검증 실패는 서비스가 ValidationError(422) → 중앙 핸들러가 매핑.
    acc = await svc.set_bank_account(principal.id, body.holder_name, body.bank, body.account_no)
    return BankAccountResponse.model_validate(acc)


@router.get("/me/payouts/payable", response_model=PayableResponse)
async def my_payable(
    principal: AccountPrincipal = Depends(get_current_account),
    svc: PayoutService = Depends(get_payout_service),
) -> PayableResponse:
    """현재 출금 가능한 미지급 정산 집계."""
    return PayableResponse.model_validate(await svc.payable(principal.id))


@router.post("/me/payouts", response_model=PayoutResponse, status_code=201)
async def request_payout(
    principal: AccountPrincipal = Depends(get_current_account),
    svc: PayoutService = Depends(get_payout_service),
) -> PayoutResponse:
    """출금 신청 — 미지급 정산분을 묶어 출금 배치 생성."""
    # NoBankAccount 422·NothingToPayout 422 → 중앙 핸들러
    payout = await svc.request_payout(principal.id)
    return PayoutResponse.model_validate(payout)


@router.get("/me/payouts", response_model=list[PayoutResponse])
async def my_payouts(
    principal: AccountPrincipal = Depends(get_current_account),
    svc: PayoutService = Depends(get_payout_service),
) -> list[PayoutResponse]:
    return [PayoutResponse.model_validate(p) for p in await svc.list_payouts(principal.id)]
