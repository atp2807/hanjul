"""billing API — 주문 생성/결제확인/조회."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from src.features.billing.application.order_service import OrderService
from src.features.billing.domain.models import AlreadyPaid, OrderNotFound, PaymentFailed
from src.features.billing.presentation.dependencies import get_order_service
from src.features.billing.presentation.schemas import (
    ConfirmPaymentRequest,
    CreateOrderRequest,
    OrderResponse,
    SettlementResponse,
)

router = APIRouter(prefix="/orders", tags=["billing"])


@router.post("", response_model=OrderResponse, status_code=201)
async def create_order(
    body: CreateOrderRequest, svc: OrderService = Depends(get_order_service)
) -> OrderResponse:
    order_id = await svc.create_order(body.book_id, body.buyer_account_id, body.amount, body.channel)
    order = await svc.get_order(order_id)
    return OrderResponse.model_validate(order)


@router.post("/{order_id}/confirm", response_model=SettlementResponse)
async def confirm_payment(
    order_id: UUID, body: ConfirmPaymentRequest, svc: OrderService = Depends(get_order_service)
) -> SettlementResponse:
    try:
        settlement = await svc.confirm_payment(order_id, body.pg_tx_id)
    except OrderNotFound:
        raise HTTPException(404, "order not found")
    except AlreadyPaid:
        raise HTTPException(409, "order already paid")
    except PaymentFailed:
        raise HTTPException(402, "payment verification failed")
    return SettlementResponse.model_validate(settlement)


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: UUID, svc: OrderService = Depends(get_order_service)) -> OrderResponse:
    try:
        order = await svc.get_order(order_id)
    except OrderNotFound:
        raise HTTPException(404, "order not found")
    return OrderResponse.model_validate(order)
