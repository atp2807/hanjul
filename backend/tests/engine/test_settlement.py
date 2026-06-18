"""정산 엔진 — 분배율/원천징수 (순수)."""
import pytest

from src.engine.settlement.calculate import EXTERNAL, SELF, calculate_settlement


def test_self_channel_70_percent():
    b = calculate_settlement(10000, SELF)
    assert b.author_gross == 7000
    assert b.platform_fee == 3000
    assert b.withholding == 231     # 7000 * 3.3%
    assert b.payout == 6769


def test_external_channel_60_percent():
    b = calculate_settlement(10000, EXTERNAL)
    assert b.author_gross == 6000
    assert b.platform_fee == 4000
    assert b.withholding == 198     # 6000 * 3.3%
    assert b.payout == 5802


def test_corporate_no_withholding():
    b = calculate_settlement(10000, SELF, is_individual=False)
    assert b.withholding == 0
    assert b.payout == b.author_gross == 7000


def test_fee_plus_gross_equals_sale_always():
    for amount in (0, 1, 999, 10000, 33333, 1234567):
        for ch in (SELF, EXTERNAL):
            b = calculate_settlement(amount, ch)
            assert b.platform_fee + b.author_gross == amount


def test_payout_never_exceeds_gross():
    b = calculate_settlement(50000, SELF)
    assert b.payout <= b.author_gross


def test_invalid_channel_raises():
    with pytest.raises(ValueError):
        calculate_settlement(1000, "UNKNOWN")


def test_negative_amount_raises():
    with pytest.raises(ValueError):
        calculate_settlement(-1, SELF)
