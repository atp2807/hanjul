"""ReportService 단위 — 접수 검증 + 처리(RESOLVE/DISMISS) (Fake repo)."""
import uuid
from datetime import UTC, datetime

import pytest
from src.features.reports.application.report_service import ReportService
from src.features.reports.domain.models import (
    DISMISSED,
    OPEN,
    RESOLVED,
    InvalidTarget,
    ReportNotFound,
)

from tests.fixtures.fake_report_repo import FakeReportRepository

NOW = datetime(2026, 7, 1, tzinfo=UTC)


# ── 접수 검증 ─────────────────────────────────────────
async def test_submit_rejects_invalid_target_type():
    svc = ReportService(FakeReportRepository())
    with pytest.raises(InvalidTarget):
        await svc.submit(uuid.uuid4(), "USER", uuid.uuid4(), "사유")


async def test_submit_normalizes_lowercase_target_type():
    svc = ReportService(FakeReportRepository())
    report = await svc.submit(uuid.uuid4(), "book", uuid.uuid4(), "사유")
    assert report.target_type == "BOOK"


async def test_submit_rejects_empty_reason():
    svc = ReportService(FakeReportRepository())
    with pytest.raises(ValueError):
        await svc.submit(uuid.uuid4(), "BOOK", uuid.uuid4(), "")


async def test_submit_rejects_whitespace_only_reason():
    svc = ReportService(FakeReportRepository())
    with pytest.raises(ValueError):
        await svc.submit(uuid.uuid4(), "BOOK", uuid.uuid4(), "   ")


async def test_submit_creates_open_report_with_trimmed_reason():
    svc = ReportService(FakeReportRepository())
    reporter_id, target_id = uuid.uuid4(), uuid.uuid4()

    report = await svc.submit(reporter_id, "REVIEW", target_id, "  스팸이에요  ")

    assert report.status == OPEN
    assert report.reason == "스팸이에요"
    assert report.reporter_id == reporter_id
    assert report.target_id == target_id


async def test_submit_allows_anonymous_reporter():
    svc = ReportService(FakeReportRepository())
    report = await svc.submit(None, "ACCOUNT", uuid.uuid4(), "사유")
    assert report.reporter_id is None


# ── 목록 ──────────────────────────────────────────────
async def test_list_open_default_filters_open_status():
    repo = FakeReportRepository()
    svc = ReportService(repo)
    await svc.submit(uuid.uuid4(), "BOOK", uuid.uuid4(), "사유1")
    r2 = await svc.submit(uuid.uuid4(), "BOOK", uuid.uuid4(), "사유2")
    await repo.resolve(r2.id, RESOLVED, uuid.uuid4(), None, NOW)

    open_reports = await svc.list_open()

    assert len(open_reports) == 1
    assert open_reports[0].status == OPEN


async def test_list_open_respects_limit_and_offset():
    repo = FakeReportRepository()
    svc = ReportService(repo)
    for i in range(3):
        await svc.submit(uuid.uuid4(), "BOOK", uuid.uuid4(), f"사유{i}")

    page = await svc.list_open(limit=1, offset=1)

    assert len(page) == 1


# ── 처리 ──────────────────────────────────────────────
async def test_resolve_raises_not_found_for_missing_report():
    svc = ReportService(FakeReportRepository())
    with pytest.raises(ReportNotFound):
        await svc.resolve(uuid.uuid4(), uuid.uuid4(), "RESOLVE", "조치완료", now=NOW)


async def test_resolve_rejects_invalid_action():
    repo = FakeReportRepository()
    svc = ReportService(repo)
    report = await svc.submit(uuid.uuid4(), "BOOK", uuid.uuid4(), "사유")

    with pytest.raises(ValueError):
        await svc.resolve(report.id, uuid.uuid4(), "DELETE", None, now=NOW)


async def test_resolve_action_resolve_sets_resolved_status():
    repo = FakeReportRepository()
    svc = ReportService(repo)
    report = await svc.submit(uuid.uuid4(), "BOOK", uuid.uuid4(), "사유")
    operator_id = uuid.uuid4()

    status = await svc.resolve(report.id, operator_id, "RESOLVE", "조치완료", now=NOW)

    assert status == RESOLVED
    stored = repo.reports[report.id]
    assert stored.status == RESOLVED
    assert stored.resolved_by == operator_id
    assert stored.resolution == "조치완료"
    assert stored.resolved_at == NOW


async def test_resolve_action_dismiss_sets_dismissed_status():
    repo = FakeReportRepository()
    svc = ReportService(repo)
    report = await svc.submit(uuid.uuid4(), "BOOK", uuid.uuid4(), "사유")

    status = await svc.resolve(report.id, uuid.uuid4(), "DISMISS", None, now=NOW)

    assert status == DISMISSED
    assert repo.reports[report.id].status == DISMISSED


async def test_resolve_action_is_case_insensitive():
    repo = FakeReportRepository()
    svc = ReportService(repo)
    report = await svc.submit(uuid.uuid4(), "BOOK", uuid.uuid4(), "사유")

    status = await svc.resolve(report.id, uuid.uuid4(), "resolve", None, now=NOW)

    assert status == RESOLVED
