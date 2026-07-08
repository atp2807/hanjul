"""email 도메인 — 메시지 값 객체 + 순수 거래 이메일 템플릿.

거래 이메일(주문확인·출금상태 안내) 전용 — 마케팅/뉴스레터는 범위 밖.
프레임워크/네트워크 의존 없는 순수 함수라 단위테스트가 가볍다.
"""
from dataclasses import dataclass


@dataclass
class EmailMessage:
    to: str
    subject: str
    html: str
    text: str


def order_confirmation_email(to: str, book_title: str, amount: int) -> EmailMessage:
    """구매 완료 확인 메일 — 결제확인(billing) best-effort 훅에서 호출."""
    amount_fmt = f"{amount:,}"
    subject = f"[한줄] 구매 완료 — {book_title}"
    html = (
        "<!doctype html><html><body>"
        "<p>안녕하세요, 한줄입니다.</p>"
        f"<p><strong>{book_title}</strong> 구매가 완료되었어요.</p>"
        f"<p>결제 금액: {amount_fmt}원</p>"
        "<p>서재에서 바로 읽으실 수 있어요. 이용해 주셔서 감사합니다.</p>"
        "</body></html>"
    )
    text = (
        f"{book_title} 구매가 완료되었어요.\n"
        f"결제 금액: {amount_fmt}원\n"
        "서재에서 바로 읽으실 수 있어요. 이용해 주셔서 감사합니다."
    )
    return EmailMessage(to=to, subject=subject, html=html, text=text)


# 출금 상태별 문구 — payouts.domain.models 의 APPROVED/PAID/REJECTED 문자열과 그대로 매칭.
# email 도메인은 payouts 도메인을 모른다(문자열 계약만 공유) — 값을 재정의하지 않고 그대로 받는다.
_STATUS_LABEL = {"APPROVED": "승인", "PAID": "지급완료", "REJECTED": "반려"}
_STATUS_BODY = {
    "APPROVED": "출금 신청이 승인되었어요. 곧 지급될 예정입니다.",
    "PAID": "출금이 지급완료되었어요. 등록하신 계좌를 확인해 주세요.",
    "REJECTED": "출금 신청이 반려되었어요. 계좌 정보를 다시 확인해 주세요.",
}


def payout_status_email(to: str, status: str, net_amt: int) -> EmailMessage:
    """출금 상태(APPROVED/PAID/REJECTED) 안내 메일 — potato 운영자 처리 best-effort 훅에서 호출."""
    label = _STATUS_LABEL.get(status, status)
    body = _STATUS_BODY.get(status, f"출금 상태가 {status}(으)로 변경되었어요.")
    amount_fmt = f"{net_amt:,}"
    subject = f"[한줄] 출금 {label} 안내"
    html = (
        "<!doctype html><html><body>"
        "<p>안녕하세요, 한줄입니다.</p>"
        f"<p>{body}</p>"
        f"<p>지급액(세후): {amount_fmt}원</p>"
        "</body></html>"
    )
    text = f"{body}\n지급액(세후): {amount_fmt}원"
    return EmailMessage(to=to, subject=subject, html=html, text=text)
