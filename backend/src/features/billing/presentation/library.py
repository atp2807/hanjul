"""내 서재 — GET /api/me/library (구매한 책)."""
from fastapi import APIRouter, Depends

from src.features.auth.domain.models import AccountPrincipal
from src.features.auth.presentation.dependencies import get_current_account
from src.features.billing.application.order_service import OrderService
from src.features.billing.presentation.dependencies import get_order_service
from src.features.billing.presentation.schemas import LibraryItemResponse, SalesSummaryResponse

router = APIRouter(tags=["library"])


@router.get("/me/library", response_model=list[LibraryItemResponse])
async def my_library(
    principal: AccountPrincipal = Depends(get_current_account),
    svc: OrderService = Depends(get_order_service),
) -> list[LibraryItemResponse]:
    books = await svc.list_library(principal.id)
    return [
        LibraryItemResponse(
            book_id=b.book_id, title=b.title, kind=b.kind, price_amt=b.price_amt,
            cover_url=b.cover_url, order_id=b.order_id,
        )
        for b in books
    ]


@router.get("/me/sales", response_model=SalesSummaryResponse)
async def my_sales(
    principal: AccountPrincipal = Depends(get_current_account),
    svc: OrderService = Depends(get_order_service),
) -> SalesSummaryResponse:
    summary = await svc.author_sales(principal.id)
    return SalesSummaryResponse.model_validate(summary)
