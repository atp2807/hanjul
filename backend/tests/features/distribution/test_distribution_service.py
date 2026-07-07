"""DistributionService — 전송 성공/실패를 항상 기록 (Fake 채널/레포)."""
import uuid
from datetime import UTC, datetime

from src.features.distribution.application.distribution_service import DistributionService
from src.features.distribution.domain.models import DistributionView


class FakeChannel:
    def __init__(self, channel="KYOBO", fail=False):
        self.channel = channel
        self.fail = fail
        self.delivered = []

    async def deliver(self, reference, epub, onix, filename):
        if self.fail:
            raise RuntimeError("sftp down")
        self.delivered.append((reference, filename))


class FakeDistRepo:
    def __init__(self):
        self.records = []

    async def record(self, book_id, channel, status, message):
        v = DistributionView(
            id=uuid.uuid4(), book_id=book_id, channel=channel,
            status=status, message=message, created_at=datetime.now(UTC),
        )
        self.records.append(v)
        return v

    async def list_for_book(self, book_id):
        return [r for r in self.records if r.book_id == book_id]


async def test_success_records_sent():
    ch, repo = FakeChannel(), FakeDistRepo()
    r = await DistributionService(repo, ch).distribute(uuid.uuid4(), b"epub", "<onix/>", "f")
    assert r.status == "SENT"
    assert ch.delivered


async def test_failure_records_failed_without_raising():
    ch, repo = FakeChannel(fail=True), FakeDistRepo()
    r = await DistributionService(repo, ch).distribute(uuid.uuid4(), b"e", "<x/>", "f")
    assert r.status == "FAILED"
    assert "sftp down" in r.message  # 감사추적: 실패도 기록
