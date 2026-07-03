"""국세청 사업자등록정보 상태조회 Open API(odcloud) 어댑터."""
import httpx

from src.features.bizverify.domain.models import BusinessRegistration
from src.shared.errors import UpstreamError

_STATUS_NAME = {"01": "계속사업자", "02": "휴업자", "03": "폐업자"}


class NtsBusinessRegistry:
    """실제 국세청 조회. API 키 미설정 시 명시적 에러(운영 배포 전 확인용)."""

    _URL = "https://api.odcloud.kr/api/nts-businessman/v1/status"

    def __init__(self, api_key: str):
        self._api_key = api_key

    async def lookup(self, business_no: str) -> BusinessRegistration | None:
        if not self._api_key:
            raise RuntimeError("NTS_BUSINESS_API_KEY 미설정 — 사업자 진위확인 비활성")
        digits = business_no.replace("-", "").replace(" ", "")
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(
                    self._URL,
                    headers={
                        "Authorization": f"Infuser {self._api_key}",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    json={"b_no": [digits]},
                )
        except httpx.RequestError as e:
            raise UpstreamError("국세청 서버에 연결할 수 없어요.") from e
        if res.status_code != 200:
            raise UpstreamError(f"국세청 조회 실패 (HTTP {res.status_code})")
        try:
            data = res.json()
        except ValueError as e:
            raise UpstreamError("국세청 응답 형식이 올바르지 않아요.") from e
        rows = data.get("data") or []
        if not rows:
            return None
        row = rows[0]
        status = row.get("b_stt_cd", "")
        return BusinessRegistration(
            business_no=digits,
            name=row.get("company") or row.get("b_nm"),
            ceo_name=row.get("p_nm"),
            status=status,
            status_name=_STATUS_NAME.get(status, "알 수 없음"),
            is_active=status == "01",
        )
