"""reports API — 고객 신고 접수 (POST /api/reports).

운영자측 목록/처리는 potato 영역(potato/presentation/reports.py)에 분리.
"""
from fastapi import APIRouter, Depends

from src.features.auth.domain.models import AccountPrincipal
from src.features.auth.presentation.dependencies import get_current_account
from src.features.reports.application.report_service import ReportService
from src.features.reports.domain.models import InvalidTarget
from src.features.reports.presentation.dependencies import get_report_service
from src.features.reports.presentation.schemas import SubmitReportRequest, SubmitReportResponse
from src.shared.errors import ValidationError

router = APIRouter(tags=["reports"])


@router.post("/reports", response_model=SubmitReportResponse, status_code=201)
async def submit_report(
    body: SubmitReportRequest,
    principal: AccountPrincipal = Depends(get_current_account),
    svc: ReportService = Depends(get_report_service),
) -> SubmitReportResponse:
    """책·리뷰·유저 신고. 로그인 필요."""
    try:
        report = await svc.submit(principal.id, body.target_type, body.target_id, body.reason)
    except InvalidTarget:
        raise ValidationError("invalid target type")
    except ValueError as e:
        raise ValidationError(str(e))
    return SubmitReportResponse(id=report.id)
