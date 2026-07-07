# 한줄 (hanjul) — 글로벌 ebook 출판 플랫폼

유페이퍼의 세련된 버전. 작가가 직접 출판·판매·정산하는 셀프퍼블리싱 + GitHub식 ebook 저작툴.
**포커스 = 개인책(단권) 셀프퍼블리싱.** 회차성 웹소설 연재는 P2(보류).

> 동명의 옛 세무 API "한줄"과 무관 — 그건 `../hanjul_tax`, `../hanjul_woncheon` 등 별도 레포.

## 스택 / 아키텍처
- 백엔드 `backend/`: FastAPI + SQLAlchemy 2.0 async + PostgreSQL(asyncpg), 런타임 Python 3.12.
- 프론트 `web/`: React 19 + Vite + **순수 JS/JSX (TypeScript 금지)**. 리더는 Pretext.js(CJK keep-all).
- **헥사고날**: feature별 `domain/ application/ infrastructure/ presentation/`. 외부 연동은 포트 뒤 + Fake 테스트.
- DB 스키마: `pub`(book/chapter/block) · `usr`(account/credential) · `bill`(주문/정산) · `dist`(배포) · `doc`(한줄독 document/share_link). 마이그레이션 alembic 0001~.
- 한줄독(문서 열람·편집, 구 juldoc 편입): 엔진 `backend/src/engine/doc/` · 기능
  `backend/src/features/doc/` · 코어 `packages/doc/`(dialect/measure/paginate, `@hanjul/doc`) ·
  프론트 `/doc`·`/doc/:id`·`/doc/s/:token`. 비로그인 허용(ownerless 문서).

## 명령어
```bash
# 백엔드 테스트 — .venv(3.14, aiosqlite)로 실행
cd backend && .venv/bin/python -m pytest -q
# 마이그레이션 / 로컬 서버 — .venv312(3.12, asyncpg) 필수
cd backend && .venv312/bin/alembic upgrade head
cd backend && .venv312/bin/uvicorn main:app --host 127.0.0.1 --port 28000
# 프론트 컴포넌트 테스트 / 브라우저 E2E
cd web && npm test
cd web && npm run e2e   # Playwright: 실 백엔드(28100)+프론트(35200)+postgres(hanjul_e2e 재생성)
```
- **venv 두 개 주의**: 테스트는 `.venv`(3.14), 런타임·마이그레이션·E2E 백엔드는 `.venv312`(3.12). asyncpg는 3.12에만.
- CI: `.github/workflows/ci.yml` (push main/PR → backend·web·e2e 3잡).

## 컨벤션 / 함정
- **데모 게이트는 fail-closed** (운영 기본 False): `PAYMENT_DEMO`·`DISTRIBUTION_DEMO`·`COVER_DEMO`·`E2E_LOGIN_ENABLED`. 외부연동 없이 dev/E2E 동작용.
- 주문 금액은 **서버가 책 가격에서 도출** (클라이언트가 금액 못 보냄).
- DB 네이밍: Python 속성=친화명 / 컬럼=접미어(`_ts`,`_cd`,`_no`,`_yn`,`_amt`). 단수 테이블 + 스키마.
- vite proxy `changeOrigin:true` 금지(인증헤더 유실). 타겟은 `VITE_API_TARGET` env.
- 포트는 웰노운 회피: 백 28000/28100, 프론트 35173/35200.
- `.env`는 gitignore — 비밀은 채팅 말고 `backend/.env`에 직접. 통합테스트 추가 시 sqlite `schema_translate_map`에 새 스키마 추가.

## 외부 연동 (자격증명 나중 주입)
- 표지 = 외부 **novelpotato** 서비스(`../novelpotato`) `/generate-cover` 호출. `lora_id` = 캐릭터 일관성(향후 웹툰 토대).
- 결제 Portone / 서점배포 SFTP — 현재 데모, 자격증명 들어오면 실연동.

## 작업 위임 (홈 CLAUDE.md 규칙 따름)
- 탐색/전수조사/단순반복 → Haiku/Explore. 코드리뷰/경량판단 → Codex. 아키텍처/복잡버그 → Opus.
- 의사결정 등 기록은 LinkLore(`mcp__llre__*`)에.
