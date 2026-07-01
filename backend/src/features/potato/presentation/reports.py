"""potato API — 신고 큐 처리 (운영자). 접수는 reports 피처(고객측).

reports 서비스에 위임 + 처리 시 감사 기록.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

from src.features.potato.application.audit import AuditService
from src.features.potato.domain.models import OperatorPrincipal
from src.features.potato.presentation.dependencies import (
    client_ip,
    get_audit_service,
    get_current_operator,
)
from src.features.potato.presentation.schemas import ReportItem, ResolveReportRequest
from src.features.reports.application.report_service import ReportService
from src.features.reports.domain.models import ReportNotFound
from src.features.reports.presentation.dependencies import get_report_service

router = APIRouter(prefix="/potato", tags=["potato"])



@router.get("/reports", response_model=list[ReportItem])
async def list_reports(
    status: str | None = "OPEN",
    limit: int = 50,
    offset: int = 0,
    _op: OperatorPrincipal = Depends(get_current_operator),
    svc: ReportService = Depends(get_report_service),
) -> list[ReportItem]:
    reports = await svc.list_open(status=status, limit=limit, offset=offset)
    return [
        ReportItem(
            id=r.id,
            reporter_id=r.reporter_id,
            target_type=r.target_type,
            target_id=r.target_id,
            reason=r.reason,
            status=r.status,
            created_at=r.created_at,
        )
        for r in reports
    ]


@router.post("/reports/{report_id}/resolve", status_code=204)
async def resolve_report(
    report_id: UUID,
    body: ResolveReportRequest,
    request: Request,
    op: OperatorPrincipal = Depends(get_current_operator),
    svc: ReportService = Depends(get_report_service),
    audit: AuditService = Depends(get_audit_service),
) -> None:
    """RESOLVE(조치완료) 또는 DISMISS(기각)."""
    try:
        status = await svc.resolve(report_id, op.id, body.action, body.resolution)
    except ReportNotFound:
        raise HTTPException(404, "report not found")
    except ValueError as e:
        raise HTTPException(422, str(e))
    await audit.record(
        op.id,
        "RESOLVE_REPORT",
        "REPORT",
        report_id,
        {"action": body.action.upper(), "status": status, "resolution": body.resolution},
        client_ip(request),
    )
