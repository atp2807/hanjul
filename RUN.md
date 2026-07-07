# 한줄 로컬 실행 (end-to-end)

정본 → 조판 → 스토어 → 결제 → 정산 → 리더를 실제로 돌려보는 경로.

## 1. Postgres

**옵션 A — 로컬 네이티브 postgres (기본, 도커 안 씀)**
```bash
createdb hanjul_ebook        # OS 유저 = role, trust auth (Homebrew/Postgres.app 기본값)
# .env: DATABASE_URL=postgresql+asyncpg://<os-user>@127.0.0.1:5432/hanjul_ebook
```
(E2E는 `web/e2e/global-setup.js`가 `hanjul_e2e` db를 매 실행 재생성 — 별도 설정 불필요)

**옵션 B — 원격 RDS (SSH 터널)**
```bash
# 터널 (localhost:5433 → RDS). 호스트·포트·키는 비공개 — 내부 인프라 노트 참조
ssh -i <KEY.pem> -N -L 5433:<RDS_HOST>:<RDS_PORT> <USER>@<BASTION_HOST> -p <SSH_PORT>
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

## 3b. (선택) 여러 기기 동기화 — CRDT 릴레이 서버
글쓰기(`/write/:id`)는 기본 **로컬 단독**(IndexedDB, 안 날아감). 다기기 실시간 동기화를 켜려면:
```bash
cd web
npm run sync                          # ws://localhost:1234 (SYNC_PORT 로 변경)
VITE_SYNC_URL=ws://localhost:1234 npm run dev   # 프론트가 동기화 연결
```
미설정 시 동기화 없이 로컬만(오프라인 우선). ⚠️ 서버 무인증 — 운영 배포 전 인증 필요.

## 4. (선택) 라이브 외부 연동 — `.env`에 채우면 활성
| 변수 | 용도 |
|---|---|
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | 소셜 로그인 |
| `PORTONE_API_SECRET` | 결제 검증 |
| `COVER_API_URL` / `COVER_API_KEY` | AI 표지 |

## 테스트
```bash
cd backend && .venv/bin/pip install -r requirements-dev.txt && .venv/bin/pytest   # 854 passed, 3 skipped
cd web && npm test                                                                # 308 (62파일)
cd potato && npm test                                                             # 29 (6파일)
cd packages/doc && npm test                                                       # 92

# 브라우저 E2E (Playwright)
cd web && npm run e2e                          # 실 백엔드(28100)+프론트(35200)+postgres(hanjul_e2e 재생성), 72
npm run test:e2e -w packages/doc                # 조판(typeset) 실측 e2e — 백엔드/DB 불요, chromium 캔버스 실측, 14
```
상세 아키텍처(배치 기준·픽스처/헬퍼 카탈로그·자동 가드) → [docs/testing.md](docs/testing.md).
