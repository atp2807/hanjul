"""샘플 책 + 정본을 실 DB(DATABASE_URL)에 시드.

사용: backend 디렉토리에서  .venv/bin/python scripts/seed.py
출력된 bookId 로 리더 접속: http://localhost:5173/?bookId=<bookId>
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.database import get_session_factory  # noqa: E402
from src.features.books.application.book_service import BookService  # noqa: E402
from src.features.books.infrastructure.book_repo import SqlBookRepository  # noqa: E402

SAMPLE = """# 한 줄

## 프롤로그

베스트셀러인데, 왜 작가는 돈을 못 벌까. 이 한 줄의 질문에서 모든 것이 시작되었다.

출판과 유통의 오랜 구조는 작가를 가장 끝자리에 두었다. 책이 팔릴수록 중간의 손들이 먼저 가져갔고, 정작 글을 쓴 사람의 몫은 마지막에야, 그것도 희미하게 남았다.

> 글은 한 줄에서 시작한다. 수익도 한 줄에서 투명해야 한다.

---

한줄은 그 구조를 다시 짠다. 작가가 직접 출판하고, 직접 판매하고, 분배율을 숨기지 않는다. 세계 어디서든 읽히도록, 그리고 어디서든 정당하게 정산되도록."""


async def main() -> None:
    factory = get_session_factory()
    async with factory() as session:
        svc = BookService(SqlBookRepository(session))
        book_id = await svc.create_book(title="한 줄", kind="BOOK", language="ko")
        result = await svc.import_text(book_id, SAMPLE, chapter_title="프롤로그")
    print(f"✅ 시드 완료 — bookId={book_id} (블록 {result.block_count}개)")
    print(f"   리더: http://localhost:5173/?bookId={book_id}")


if __name__ == "__main__":
    asyncio.run(main())
