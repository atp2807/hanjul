# 한줄 로컬 실행 (end-to-end)

정본 → 조판 → 스토어 → 결제 → 정산 → 리더를 실제로 돌려보는 경로.

## 1. Postgres

**옵션 A — 로컬 docker**
```bash
docker compose up -d        # postgres:16, :5432
# .env: DATABASE_URL=postgresql+asyncpg://hanjul:hanjul@localhost:5432/hanjul
```

**옵션 B — 원격 RDS (SSH 터널)** ← 현재 셋업
```bash
# 터널 (localhost:5433 → RDS)
ssh -i <key.pem> -N -L 5433:<RDS_HOST>:<RDS_PORT> ubuntu@<BASTION_HOST> -p <SSH_PORT>
# .env: DATABASE_URL=postgresql+asyncpg://<user>:<pw>@127.0.0.1:5433/hanjul_ebook
# (전용 DB hanjul_ebook 사용 — 운영 데이터와 격리)
```

## 2. 백엔드 (Python 3.12)
```bash
cd backend
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
.venv/bin/alembic upgrade head        # 스키마 생성: pub / usr / bill
.venv/bin/python scripts/seed.py      # 샘플 한글책 시드 → bookId 출력
.venv/bin/uvicorn main:app --port 28000 --reload   # http://localhost:28000  (문서 /docs)
```

## 3. 리더 (다른 터미널)
```bash
cd web
npm install
npm run dev                           # http://localhost:35173
```
브라우저에서 **`http://localhost:35173/?bookId=<2번에서 출력된 bookId>`** 열기:
- 샘플 한글책이 **Pretext로 조판**되어 페이지로 표시
- **A+/A-** → 즉시 재조판 / **이전·다음** → 페이지 넘김

## 4. (선택) 라이브 외부 연동 — `.env`에 채우면 활성
| 변수 | 용도 |
|---|---|
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | 소셜 로그인 |
| `PORTONE_API_SECRET` | 결제 검증 |
| `COVER_API_URL` / `COVER_API_KEY` | AI 표지 |

## 테스트
```bash
cd backend && .venv/bin/pip install -r requirements-dev.txt && .venv/bin/pytest   # 62
cd web && npm test                                                                # 6
```
