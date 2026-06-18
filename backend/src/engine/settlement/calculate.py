"""정산 계산 (순수 함수, stdlib만). 분배율 투명 + 원천징수.

판매 채널별 작가 분배율 (lr-635fa8cc 기준선):
  SELF     자체판매 → 작가 70% (플랫폼 수수료 30%)
  EXTERNAL 외부서점 → 작가 60% (수수료 40%, 서점 몫 포함)
개인 작가는 작가 몫에서 3.3%(소득세 3% + 주민세 0.3%) 원천징수 후 지급.
"""
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

SELF = "SELF"
EXTERNAL = "EXTERNAL"

AUTHOR_RATE = {SELF: Decimal("0.70"), EXTERNAL: Decimal("0.60")}
WITHHOLDING_RATE = Decimal("0.033")  # 소득세 3% + 주민세 0.3%


@dataclass(frozen=True)
class SettlementBreakdown:
    sale_amount: int     # 판매가
    channel: str         # SELF | EXTERNAL
    author_gross: int    # 작가 몫(원천징수 전)
    platform_fee: int    # 플랫폼/서점 수수료
    withholding: int     # 원천징수액 (개인 3.3%)
    payout: int          # 실지급액 = author_gross - withholding


def _won(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def calculate_settlement(sale_amount: int, channel: str, is_individual: bool = True) -> SettlementBreakdown:
    if channel not in AUTHOR_RATE:
        raise ValueError(f"unknown channel: {channel}")
    if sale_amount < 0:
        raise ValueError("sale_amount must be >= 0")

    sale = Decimal(sale_amount)
    author_gross = _won(sale * AUTHOR_RATE[channel])
    platform_fee = sale_amount - author_gross  # 합이 정확히 판매가가 되도록 잔액으로
    withholding = _won(Decimal(author_gross) * WITHHOLDING_RATE) if is_individual else 0
    payout = author_gross - withholding

    return SettlementBreakdown(
        sale_amount=sale_amount,
        channel=channel,
        author_gross=author_gross,
        platform_fee=platform_fee,
        withholding=withholding,
        payout=payout,
    )
