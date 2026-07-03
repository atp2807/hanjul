"""사업자등록번호 체크섬 검증 (순수). 유효 샘플은 알고리즘 역산으로 체크디지트를 맞춘 값."""
from src.engine.validation.business_number import is_valid_business_number

# 아래 번호들은 실존 회사가 아니라 체크섬 알고리즘으로 마지막 자리를 역산해 만든 검증용 값.
# 2208162517: 앞 9자리(220816251) → 체크디지트 7. 하이픈 유무 모두 통과해야 함.
VALID = ["2208162517", "220-81-62517", "1234567891", "123-45-67891", "0123456782"]


def test_valid_numbers_without_hyphen():
    assert is_valid_business_number("2208162517")
    assert is_valid_business_number("1234567891")
    assert is_valid_business_number("0123456782")


def test_valid_numbers_with_hyphen():
    assert is_valid_business_number("220-81-62517")
    assert is_valid_business_number("123-45-67891")


def test_hyphen_and_plain_agree():
    for n in VALID:
        assert is_valid_business_number(n)


def test_wrong_checksum_rejected():
    # 마지막 자리만 어긋난 값 (체크섬 불일치)
    assert not is_valid_business_number("2208162516")
    assert not is_valid_business_number("1234567890")


def test_too_few_digits_rejected():
    assert not is_valid_business_number("220816251")
    assert not is_valid_business_number("123")


def test_too_many_digits_rejected():
    assert not is_valid_business_number("22081625177")


def test_non_digit_characters_rejected():
    assert not is_valid_business_number("22081625AB")
    assert not is_valid_business_number("abcdefghij")


def test_empty_string_rejected():
    assert not is_valid_business_number("")


def test_non_string_type_rejected():
    assert not is_valid_business_number(None)  # type: ignore[arg-type]
    assert not is_valid_business_number(2208162517)  # type: ignore[arg-type]
