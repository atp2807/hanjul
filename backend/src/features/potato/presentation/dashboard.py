"""potato API — 운영 대시보드 (가입·출판·차단·신고 카운트)."""
from fastapi import APIRouter, Depends

from src.features.potato.application.dashboard import DashboardService
from src.features.potato.domain.models import OperatorPrincipal
from src.features.potato.presentation.dependencies import (
    get_current_operator,
    get_dashboard_service,
)
from src.features.potato.presentation.schemas import DashboardStats

router = APIRouter(prefix="/potato", tags=["potato"])


@router.get("/dashboard/stats", response_model=DashboardStats)
async def dashboard_stats(
    _op: OperatorPrincipal = Depends(get_current_operator),
    svc: DashboardService = Depends(get_dashboard_service),
) -> DashboardStats:
    return DashboardStats(**await svc.stats())
