"""reports DI."""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_session
from src.features.reports.application.report_service import ReportService
from src.features.reports.infrastructure.report_repo import SqlReportRepository


def get_report_service(session: AsyncSession = Depends(get_session)) -> ReportService:
    return ReportService(SqlReportRepository(session))
