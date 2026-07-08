#!/usr/bin/env python3
"""woncheon 원천징수 신고 수동 재시도 (lr-ac61f505).

PAID 전이 시 best-effort 로 시도된 신고가 실패/보류된 payout을 다시 시도한다.
자동 재시도 스케줄러는 이 범위 밖(과함) — 필요할 때 운영자가 수동 실행.

사용:
  .venv312/bin/python scripts/woncheon_retry_report.py              # 미신고 전체(주민번호 등록된 것만) 재시도
  .venv312/bin/python scripts/woncheon_retry_report.py <payout_id>  # 특정 건만
"""
import argparse
import asyncio
import os
import sys
from uuid import UUID

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.database import get_session_factory  # noqa: E402
from src.config.settings import settings  # noqa: E402
from src.features.woncheon.application.reporting_service import WoncheonReportingService  # noqa: E402
from src.features.woncheon.infrastructure.withholding_repo import SqlWithholdingRepository  # noqa: E402
from src.features.woncheon.infrastructure.woncheon_adapter import build_woncheon_adapter  # noqa: E402


async def main() -> None:
    ap = argparse.ArgumentParser(description="woncheon 미신고 payout 수동 재시도")
    ap.add_argument("payout_id", nargs="?", help="특정 payout id (생략 시 미신고 전체)")
    args = ap.parse_args()

    factory = get_session_factory()
    async with factory() as session:
        repo = SqlWithholdingRepository(session)
        port = build_woncheon_adapter(settings)
        svc = WoncheonReportingService(repo, port, settings.WONCHEON_DEFAULT_INCOME_TYPE_CODE or None)

        if args.payout_id:
            targets = [UUID(args.payout_id)]
        else:
            targets = [v.payout_id for v in await svc.list_unreported() if v.has_subject]

        if not targets:
            print("재시도할 대상 없음 (주민번호 미등록 건은 제외 — 먼저 PUT /potato/payouts/{id}/withholding-subject 로 등록)")
            return

        for payout_id in targets:
            result = await svc.report_paid(payout_id)
            status = "OK" if result.ok else f"보류/실패: {result.message}"
            print(f"{payout_id}: {status}")


if __name__ == "__main__":
    asyncio.run(main())
