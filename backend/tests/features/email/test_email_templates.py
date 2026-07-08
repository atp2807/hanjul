"""이메일 순수 템플릿 — 주문확인 1케이스 + 출금상태 APPROVED/PAID/REJECTED 3케이스."""
from src.features.email.domain.models import order_confirmation_email, payout_status_email


def test_order_confirmation_email_contains_key_values():
    msg = order_confirmation_email("reader@x.com", "바이브코딩 첫걸음", 12000)

    assert msg.to == "reader@x.com"
    assert "바이브코딩 첫걸음" in msg.subject
    assert "구매 완료" in msg.subject
    assert "바이브코딩 첫걸음" in msg.html
    assert "12,000" in msg.html
    # text 폴백 — HTML 클라이언트가 아니어도 핵심 정보 확인 가능, 태그 없는 순수 텍스트
    assert "바이브코딩 첫걸음" in msg.text
    assert "12,000" in msg.text
    assert "<" not in msg.text


def test_payout_status_email_approved():
    msg = payout_status_email("author@x.com", "APPROVED", 9670)

    assert msg.to == "author@x.com"
    assert "승인" in msg.subject
    assert "9,670" in msg.html
    assert "9,670" in msg.text
    assert "<" not in msg.text


def test_payout_status_email_paid():
    msg = payout_status_email("author@x.com", "PAID", 9670)

    assert "지급완료" in msg.subject
    assert "지급완료" in msg.html
    assert "9,670" in msg.text


def test_payout_status_email_rejected():
    msg = payout_status_email("author@x.com", "REJECTED", 9670)

    assert "반려" in msg.subject
    assert "반려" in msg.html
    assert "9,670" in msg.text
