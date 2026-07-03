"""bizverify 도메인 — 국세청 사업자등록 진위확인 결과 + 포트 + 에러."""
from dataclasses import dataclass
from typing import Protocol

from src.shared.errors import NotFoundError, ValidationError


@dataclass
class BusinessRegistration:
    business_no: str      # 하이픈 제거 10자리
    name: str | None      # 상호
    ceo_name: str | None  # 대표자명
    status: str           # 01=계속사업자 02=휴업자 03=폐업자
    status_name: str      # 한글 상태명
    is_active: bool       # status == "01"


class InvalidBusinessNumber(ValidationError):
    default_detail = "사업자등록번호 형식이 올바르지 않아요."


class BusinessNotRegistered(NotFoundError):
    default_detail = "등록된 사업자를 찾을 수 없어요."


class BusinessRegistryPort(Protocol):
    async def lookup(self, business_no: str) -> BusinessRegistration | None:
        """국세청에 등록된 사업자 정보 조회. 없으면 None. 외부 연동 실패 시 UpstreamError."""
        ...
