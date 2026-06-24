"""NotificationService 단위 — 팔로우 규칙 + 신간 팬아웃."""
import uuid

import pytest

from src.features.notifications.application.notification_service import NotificationService
from tests.fixtures.fake_notification_repo import FakeFollowRepository, FakeNotificationRepository


def _svc():
    return NotificationService(FakeFollowRepository(), FakeNotificationRepository())


async def test_self_follow_rejected():
    svc = _svc()
    me = uuid.uuid4()
    with pytest.raises(ValueError):
        await svc.follow(me, me)


async def test_notify_only_followers_excludes_author():
    svc = _svc()
    author, f1, f2, stranger = (uuid.uuid4() for _ in range(4))
    await svc.follow(f1, author)
    await svc.follow(f2, author)
    book = uuid.uuid4()

    sent = await svc.notify_new_book(book, author, "신간")
    assert sent == 2

    for f in (f1, f2):
        items, unread = await svc.inbox(f)
        assert unread == 1 and items[0].book_id == book and items[0].title == "신간"
    # 팔로우 안 한 사람 · 작가 본인은 0
    assert (await svc.inbox(stranger))[1] == 0
    assert (await svc.inbox(author))[1] == 0


async def test_notify_no_author_is_noop():
    svc = _svc()
    assert await svc.notify_new_book(uuid.uuid4(), None, "익명책") == 0


async def test_mark_read_and_all():
    svc = _svc()
    author, follower = uuid.uuid4(), uuid.uuid4()
    await svc.follow(follower, author)
    await svc.notify_new_book(uuid.uuid4(), author, "A")
    await svc.notify_new_book(uuid.uuid4(), author, "B")

    items, unread = await svc.inbox(follower)
    assert unread == 2
    assert await svc.mark_read(follower, items[0].id) is True
    assert (await svc.inbox(follower))[1] == 1
    await svc.mark_all_read(follower)
    assert (await svc.inbox(follower))[1] == 0


async def test_unfollow_stops_future_notifications():
    svc = _svc()
    author, follower = uuid.uuid4(), uuid.uuid4()
    await svc.follow(follower, author)
    await svc.unfollow(follower, author)
    assert await svc.notify_new_book(uuid.uuid4(), author, "신간") == 0
