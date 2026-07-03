"""테스트용 Fake 등급 분류기 — 고정 결과 반환 또는 예외 주입."""
from src.features.books.domain.content_rating import category_keys


class FakeContentRatingClassifier:
    def __init__(self, result: dict[str, str] | None = None, error: Exception | None = None):
        # 기본: 전부 ALL. result로 일부만 지정하면 나머지는 ALL로 채움.
        base = {k: "ALL" for k in category_keys()}
        if result:
            base.update(result)
        self._result = base
        self._error = error
        self.calls: list[str] = []

    async def classify(self, text: str) -> dict[str, str]:
        self.calls.append(text)
        if self._error is not None:
            raise self._error
        return dict(self._result)
