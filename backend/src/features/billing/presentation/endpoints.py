"""billing API — 주문 생성/결제확인/조회 + 결제 설정."""
from uuid import UUID

from fastapi import APIRouter, Depends

from src.config.settings import settings
from src.features.auth.domain.models import AccountPrincipal
from src.features.auth.presentation.dependencies import get_current_account
from src.features.billing.application.order_service import OrderService
from src.features.billing.domain.models import (
    AlreadyOwned,
    AlreadyPaid,
    ConsentRequired,
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
from src.shared.errors import NotFoundError

router = APIRouter(prefix="/orders", tags=["billing"])
payments_router = APIRouter(prefix="/payments", tags=["billing"])


@payments_router.get("/config")
async def payment_config() -> dict:
    """프론트 결제 위젯 초기화용 공개 설정. clientKey는 공개키(test_ck_)라 노출 OK."""
    return {"demo": settings.PAYMENT_DEMO, "tossClientKey": settings.TOSS_TEST_CLIENT_KEY}


@payments_router.post("/webhook")
async def toss_webhook(
    body: dict, svc: OrderService = Depends(get_order_service)
) -> dict:
    """토스 웹훅 — 대시보드 취소 등으로 결제 상태 바뀌면 우리 주문과 동기화.

    바디는 신뢰하지 않음(인증 없음). orderId만 꺼내 PG에서 실제 상태를 재조회해
    취소면 환불 처리. 토스 재시도 방지 위해 항상 200.
    """
    data = body.get("data") if isinstance(body.get("data"), dict) else {}
    order_id = data.get("orderId") or body.get("orderId")
    if order_id:
        try:
            await svc.reconcile_canceled(UUID(str(order_id)))
        except (ValueError, OrderNotFound):
            pass
        except Exception:  # noqa: BLE001 — 어떤 경우든 토스엔 200
            pass
    return {"ok": True}


@router.post("", response_model=OrderResponse, status_code=201)
async def create_order(
    body: CreateOrderRequest,
    principal: AccountPrincipal = Depends(get_current_account),
    svc: OrderService = Depends(get_order_service),
) -> OrderResponse:
    # 구매자 = 인증된 사용자, 금액 = 서버가 책 가격에서 도출 (클라 입력 안 받음)
    # 도메인 예외(ConsentRequired 422·NotPurchasable 404·AlreadyOwned 409)는 중앙 핸들러가 매핑.
    order_id = await svc.create_order(
        body.book_id, principal.id, body.channel, withdrawal_consent=body.withdrawal_consent
    )
    order = await svc.get_order(order_id)
    return OrderResponse.model_validate(order)


@router.post("/{order_id}/confirm", response_model=SettlementResponse)
async def confirm_payment(
    order_id: UUID,
    body: ConfirmPaymentRequest,
    principal: AccountPrincipal = Depends(get_current_account),
    svc: OrderService = Depends(get_order_service),
) -> SettlementResponse:
    # OrderNotFound 404·AlreadyPaid 409·PaymentFailed 402 → 중앙 핸들러
    settlement = await svc.confirm_payment(order_id, body.pg_tx_id, buyer_id=principal.id)
    return SettlementResponse.model_validate(settlement)


@router.post("/{order_id}/refund", status_code=204)
async def refund_order(
    order_id: UUID,
    principal: AccountPrincipal = Depends(get_current_account),
    svc: OrderService = Depends(get_order_service),
) -> None:
    """구매자 본인 환불 — PG 취소 + 서재 권한 회수. 미결제/이미환불 409, PG 거절 402."""
    # OrderNotFound 404·NotRefundable 409·RefundFailed 402 → 중앙 핸들러
    await svc.refund(order_id, buyer_id=principal.id)


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: UUID,
    principal: AccountPrincipal = Depends(get_current_account),
    svc: OrderService = Depends(get_order_service),
) -> OrderResponse:
    order = await svc.get_order(order_id)  # OrderNotFound → 404 (중앙 핸들러)
    # 본인 주문만 — 타인 주문은 존재 노출 없이 404 (인가는 표현층 판단)
    if order.buyer_account_id != principal.id:
        raise NotFoundError("order not found")
    return OrderResponse.model_validate(order)
