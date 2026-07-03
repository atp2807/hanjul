"""사업자등록번호 체크섬 검증 (순수 함수, stdlib만). 국세청 표준 검증 알고리즘."""


def is_valid_business_number(business_no: str) -> bool:
    """10자리 사업자등록번호(하이픈 포함/미포함 모두 허용)의 체크섬이 유효한지 검사."""
    if not isinstance(business_no, str):
        return False
    digits = business_no.replace("-", "").replace(" ", "")
    if len(digits) != 10 or not digits.isdigit():
        return False
    multipliers = [1, 3, 7, 1, 3, 7, 1, 3, 5, 1]
    checksum = sum(int(digits[i]) * multipliers[i] for i in range(9))
    checksum += (int(digits[8]) * 5) // 10
    check_digit = (10 - (checksum % 10)) % 10
    return int(digits[9]) == check_digit
