"""bizverify 테스트용 Fake — 국세청 조회 포트. 외부 호출 없이 미리 세팅한 값 반환."""


class FakeBusinessRegistry:
    def __init__(self, result=None):
        self._result = result  # BusinessRegistration | None, 미리 세팅

    async def lookup(self, business_no):
        return self._result
