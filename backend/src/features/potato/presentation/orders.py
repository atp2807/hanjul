"""potato API — 운영자 주문 환불 집행 (Phase 2, A).

구매자 본인 환불(billing.presentation.endpoints.refund_order)과 달리 buyer_id 제약이
없다 — 운영자가 임의 주문을 조회해 환불할 수 있다. moderation.py의 takedown 패턴과
동형: 서비스에 위임 + 감사 기록 + best-effort 안내메일.

⚠️ 정산(Settlement) 역처리는 범위 밖(후속 과제) — order_service.refund_by_operator의
mark_refunded는 order.status만 REFUNDED로 바꾸고, 이미 계산된 Settlement/출금가능잔액은
그대로 남는다(기존 구매자 self-refund와 동일한 한계).
"""
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from src.features.accounts.application.account_service import AccountService
from src.features.accounts.presentation.dependencies import get_account_service
from src.features.billing.application.order_service import OrderService
from src.features.billing.presentation.dependencies import get_order_service
from src.features.catalog.application.catalog_service import CatalogService
from src.features.catalog.presentation.dependencies import get_catalog_service
from src.features.email.domain.models import order_refund_email
from src.features.email.domain.ports import EmailSender
from src.features.email.presentation.dependencies import get_email_sender
from src.features.potato.application.audit import AuditService
from src.features.potato.domain.models import OperatorPrincipal
from src.features.potato.presentation.dependencies import (
    client_ip,
    get_audit_service,
    get_current_operator,
)
from src.features.potato.presentation.schemas import OrderOpsItem, RefundOrderRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/potato", tags=["potato"])


@router.get("/orders", response_model=list[OrderOpsItem])
async def list_orders(
    status: str | None = "PAID",
    limit: int = 50,
    offset: int = 0,
    _op: OperatorPrincipal = Depends(get_current_operator),
    svc: OrderService = Depends(get_order_service),
) -> list[OrderOpsItem]:
    """운영자 주문 목록 — 환불 대상 탐색용(구매자 제약 없음, 최신순)."""
    return [OrderOpsItem.model_validate(o) for o in await svc.list_for_ops(status, limit, offset)]


async def _notify_refund_email(
    catalog: CatalogService,
    accounts: AccountService,
    email_sender: EmailSender,
    book_id: UUID,
    buyer_id: UUID,
    amount: int,
) -> None:
    """환불 안내메일 — best-effort. 실패해도 환불·감사는 이미 확정된 뒤라 안전(payouts._notify_payout_email과 동형)."""
    try:
        profile = await accounts.get_profile(buyer_id)
        if not profile.email:
            return  # 탈퇴 등으로 이메일 없음 — 조용히 스킵
        book = await catalog.get_meta(book_id)
        await email_sender.send(order_refund_email(profile.email, book.title, amount))
    except Exception:
        logger.warning(
            "주문 환불 안내메일 실패(book=%s buyer=%s) — 환불 처리는 유지", book_id, buyer_id, exc_info=True
        )


@router.post("/orders/{order_id}/refund", status_code=204)
async def refund_order(
    order_id: UUID,
    request: Request,
    body: RefundOrderRequest = RefundOrderRequest(),
    op: OperatorPrincipal = Depends(get_current_operator),
    svc: OrderService = Depends(get_order_service),
    catalog: CatalogService = Depends(get_catalog_service),
    accounts: AccountService = Depends(get_account_service),
    audit: AuditService = Depends(get_audit_service),
    email_sender: EmailSender = Depends(get_email_sender),
) -> None:
    """운영자 임의 주문 환불 집행 — PG 취소 + PAID→REFUNDED. buyer 제약 없음(potato 전용).

    OrderNotFound 404·NotRefundable 409·RefundFailed 402 → 중앙 핸들러.
    """
    order = await svc.refund_by_operator(order_id, body.reason or "")
    await audit.record(
        op.id, "ORDER_REFUND", "ORDER", order_id, {"reason": body.reason}, client_ip(request)
    )
    await _notify_refund_email(
        catalog, accounts, email_sender, order.book_id, order.buyer_account_id, order.amount_amt
    )
