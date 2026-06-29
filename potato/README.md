# potato — 한줄 운영자 콘솔

고객 앱(`web/`)과 **완전히 분리된** 운영자 전용 앱. 별도 빌드/배포, 토큰 격리(`potato_token`),
별도 인증 영역(`/api/potato/*`, JWT `aud="potato"`). 운영자는 고객 기능에 접근 불가.

대상: potato.hanjul.io (운영). 공개가입 없음 — 계정은 서버 CLI로만 생성.

## 기능 (Phase 1 = 신뢰·안전)
- 대시보드(가입·출판·차단·신고 카운트)
- 모더레이션(책 강제 비공개 takedown / 복원)
- 신고 큐(책·리뷰·유저 신고 → 조치/기각)
- 계정(조회 → 정지 / 서평단 자격회수)
- 모든 변경은 `potato.audit_log`에 자동 감사 기록.
- 역할: OPERATOR(위 전부) / DEVELOPER(+ 향후 시스템 메뉴, devOnly nav).

## 로컬 개발
```bash
# 1) 백엔드 (potato 라우트 포함하도록 반드시 재시작)
cd ../backend && .venv312/bin/uvicorn main:app --host 127.0.0.1 --port 28000

# 2) 첫 운영자 시드 (서버 CLI, 비번은 프롬프트로)
cd ../backend && .venv312/bin/python scripts/create_operator.py you@hanjul.io 이름 --role DEVELOPER

# 3) 운영자 앱 (vite proxy /api → 28000)
npm install
npm run dev          # http://localhost:35180
```

## 운영 배포 (potato.hanjul.io)
1. **빌드**: `npm install && npm run build` → `dist/` (`.env.production`의 VITE_API_BASE_URL 사용).
2. **Cloudflare Pages**: 신규 프로젝트(예: `hanjul-potato`)로 `dist/` 배포.
   `npx wrangler@3 pages deploy dist --project-name=hanjul-potato --branch=main`
3. **커스텀 도메인**: Pages에 `potato.hanjul.io` 연결(DNS CNAME → `*.pages.dev`).
4. **⚠️ 백엔드 CORS**: `backend/.env`의 `CORS_ORIGINS`에 `https://potato.hanjul.io` 추가
   (없으면 브라우저가 api.hanjul.io 호출을 차단). 추가 후 `hanjul-api` 재시작.
5. **⚠️ prod 운영자 시드**: 서버에서 `create_operator.py` 1회 실행(비번은 채팅 아님, CLI 프롬프트).
6. **prod RDS 마이그**: `0018~0020`(potato.operator/audit_log, book.blocked_ts, commu.report).
