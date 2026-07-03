"""현재 로그인 계정(유저) — GET /api/me, PUT /api/me/profile.

인증(누구인지)은 auth 의 get_current_account 가, 유저 데이터(프로필)는 accounts 가.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from src.features.accounts.application.account_service import AccountService
from src.features.accounts.presentation.dependencies import get_account_service
from src.features.accounts.presentation.schemas import AccountResponse
from src.features.auth.domain.models import AccountPrincipal
from src.features.auth.presentation.dependencies import get_current_account
from src.features.billing.application.order_service import OrderService
from src.features.billing.presentation.dependencies import get_order_service
from src.features.billing.presentation.schemas import LibraryItemResponse, SalesSummaryResponse
from src.features.payouts.application.payout_service import PayoutService
from src.features.payouts.presentation.dependencies import get_payout_service
from src.features.payouts.presentation.schemas import BankAccountResponse, PayoutResponse

router = APIRouter(tags=["account"])


class UpdateProfileRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    bio: str | None = Field(default=None, max_length=1000)


@router.get("/me", response_model=AccountResponse)
async def me(
    principal: AccountPrincipal = Depends(get_current_account),
    svc: AccountService = Depends(get_account_service),
) -> AccountResponse:
    acc = await svc.get_profile(principal.id)
    return AccountResponse.model_validate(acc)


@router.put("/me/profile", status_code=204)
async def update_profile(
    body: UpdateProfileRequest,
    principal: AccountPrincipal = Depends(get_current_account),
    svc: AccountService = Depends(get_account_service),
) -> None:
    """작가 소개(bio) 수정."""
    await svc.update_bio(principal.id, body.bio)


@router.get("/me/export")
async def export_my_data(
    principal: AccountPrincipal = Depends(get_current_account),
    svc: AccountService = Depends(get_account_service),
    orders: OrderService = Depends(get_order_service),
    payouts: PayoutService = Depends(get_payout_service),
) -> dict:
    """개인정보 열람/다운로드 (개인정보보호법 §35 열람권).

    프로필 + 구매내역 + 판매정산 + 출금계좌(마스킹)·출금내역 — 보유 개인정보 일괄.
    """
    acc = await svc.get_profile(principal.id)
    library = await orders.list_library(principal.id)
    sales = await orders.author_sales(principal.id)
    bank = await payouts.get_bank_account(principal.id)
    payout_rows = await payouts.list_payouts(principal.id)
    return {
        "account": AccountResponse.model_validate(acc).model_dump(by_alias=True),
        "purchases": [
            LibraryItemResponse(
                book_id=b.book_id, title=b.title, kind=b.kind, price_amt=b.price_amt,
                cover_url=b.cover_url, order_id=b.order_id,
            ).model_dump(by_alias=True)
            for b in library
        ],
        "sales": SalesSummaryResponse.model_validate(sales).model_dump(by_alias=True),
        "bankAccount": (
            BankAccountResponse.model_validate(bank).model_dump(by_alias=True) if bank else None
        ),
        "payouts": [PayoutResponse.model_validate(p).model_dump(by_alias=True) for p in payout_rows],
    }


@router.delete("/me", status_code=204)
async def withdraw(
    principal: AccountPrincipal = Depends(get_current_account),
    svc: AccountService = Depends(get_account_service),
) -> None:
    """회원탈퇴 — 개인정보 익명화 + 소셜 연결 삭제.

    주문·정산 기록은 관련 법령(전자상거래법 5년)에 따라 계정 행을 익명 상태로 보존.
    """
    await svc.withdraw(principal.id)
