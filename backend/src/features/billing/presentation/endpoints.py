"""billing API — 주문 생성/결제확인/조회 + 결제 설정."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from src.config.settings import settings
from src.features.auth.domain.models import AccountPrincipal
from src.features.auth.presentation.dependencies import get_current_account
from src.features.billing.application.order_service import OrderService
from src.features.billing.domain.models import (
    AlreadyOwned,
    AlreadyPaid,
    NotPurchasable,
    NotRefundable,
    OrderNotFound,
    PaymentFailed,
    RefundFailed,
)
from src.features.billing.presentation.dependencies import get_order_service
from src.features.billing.presentation.schemas import (
    ConfirmPaymentRequest,
    CreateOrderRequest,
    OrderResponse,
    SettlementResponse,
)

router = APIRouter(prefix="/orders", tags=["billing"])
payments_router = APIRouter(prefix="/payments", tags=["billing"])


@payments_router.get("/config")
async def payment_config() -> dict:
    """프론트 결제 위젯 초기화용 공개 설정. clientKey는 공개키(test_ck_)라 노출 OK."""
    return {"demo": settings.PAYMENT_DEMO, "tossClientKey": settings.TOSS_TEST_CLIENT_KEY}


@router.post("", response_model=OrderResponse, status_code=201)
async def create_order(
    body: CreateOrderRequest,
    principal: AccountPrincipal = Depends(get_current_account),
    svc: OrderService = Depends(get_order_service),
) -> OrderResponse:
    # 구매자 = 인증된 사용자, 금액 = 서버가 책 가격에서 도출 (클라 입력 안 받음)
    try:
        order_id = await svc.create_order(body.book_id, principal.id, body.channel)
    except NotPurchasable:
        raise HTTPException(404, "book not purchasable")
    except AlreadyOwned:
        raise HTTPException(409, "already owned")
    order = await svc.get_order(order_id)
    return OrderResponse.model_validate(order)


@router.post("/{order_id}/confirm", response_model=SettlementResponse)
async def confirm_payment(
    order_id: UUID,
    body: ConfirmPaymentRequest,
    principal: AccountPrincipal = Depends(get_current_account),
    svc: OrderService = Depends(get_order_service),
) -> SettlementResponse:
    try:
        settlement = await svc.confirm_payment(order_id, body.pg_tx_id, buyer_id=principal.id)
    except OrderNotFound:
        raise HTTPException(404, "order not found")
    except AlreadyPaid:
        raise HTTPException(409, "order already paid")
    except PaymentFailed:
        raise HTTPException(402, "payment verification failed")
    return SettlementResponse.model_validate(settlement)


@router.post("/{order_id}/refund", status_code=204)
async def refund_order(
    order_id: UUID,
    principal: AccountPrincipal = Depends(get_current_account),
    svc: OrderService = Depends(get_order_service),
) -> None:
    """구매자 본인 환불 — PG 취소 + 서재 권한 회수. 미결제/이미환불 409, PG 거절 402."""
    try:
        await svc.refund(order_id, buyer_id=principal.id)
    except OrderNotFound:
        raise HTTPException(404, "order not found")
    except NotRefundable:
        raise HTTPException(409, "order not refundable")
    except RefundFailed:
        raise HTTPException(402, "refund failed")


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: UUID,
    principal: AccountPrincipal = Depends(get_current_account),
    svc: OrderService = Depends(get_order_service),
) -> OrderResponse:
    try:
        order = await svc.get_order(order_id)
    except OrderNotFound:
        raise HTTPException(404, "order not found")
    # 본인 주문만 — 타인 주문은 존재 노출 없이 404
    if order.buyer_account_id != principal.id:
        raise HTTPException(404, "order not found")
    return OrderResponse.model_validate(order)
