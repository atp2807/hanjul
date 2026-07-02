# 디자인 시스템 패키지 분리 설계 (@hanjul/ui)

> 목적: 흩어진 UI 컴포넌트를 공용 패키지로 분리 → ①web·potato 중복 제거 ②design-sync 정식 경로.
> 제약: **TypeScript 코드 0** (앱 컨벤션). 타입 계약은 JSDoc→`.d.ts` 자동생성(도구만, 코드는 JSX).
> 조사일: 2026-07-02

## 현황 (조사 결과)
- 루트 `package.json` 없음 = **workspace 미구성**. web/potato/backend 독립 디렉토리.
- **중복**: `web/src/components/ui/`(Button·Card·Badge·Chip·Field·PageHeader·Stat 7) ↔ `potato/src/ui.jsx`(같은 7 + Icon). 팔레트 브랜드색 동일(`ink:#0e4a5c`).
- theme 토큰: web 전용 `hero*·inkSoft·shadow·textMid·tint`, potato 전용 `danger·warn·ok·info(+Bg)·sidebar*·rowTint`. 브랜드색은 공통 → **union 병합 안전**.
- 소비처: web에서 theme import **34개 파일**, potato에서 theme·ui import **9개**.
- 배포: **둘 다 로컬 빌드 + `wrangler pages deploy dist` (direct upload)**. web=hanjul, potato=hanjul-ops. git 자동배포 OFF.
- 도구: node 20 / npm 11.6 (workspaces OK). `tsc` 없음(devDep 추가 필요, 로컬 전용).
- Icon: web `Icon.jsx`(고객용 20개) vs potato(운영자용 8개) — **완전 다름 → 통합 안 함, 앱별 유지.**

## 핵심 결정
1. **npm workspaces** — 루트 `package.json`에 `workspaces: ["web","potato","packages/*"]`. (별도 도구 없이 npm만). backend는 파이썬이라 제외.
2. **`packages/ui`(`@hanjul/ui`)** = 공용 프리미티브 **Button·Card·Badge·Chip·Field·PageHeader·Stat + theme(union) + coverGradient**. **Icon 제외**(앱별 아이콘셋).
2b. **`packages/lib`(`@hanjul/lib`)** = 로직 중복 정리(디자인 무관):
   - `createApiClient(tokenKey)` — fetch 래퍼(get/post/put/del/upload/download)+토큰. web=`hanjul_token`·potato=`potato_token`만 다름 → 팩토리.
   - `createAuthContext({loadUser})` — provider 패턴(token·loading·login·logout) 팩토리. 앱은 loadUser(getMe/api.me)·필드명(user/operator)만 주입.
   - 엔드포인트별 메서드(login·dashboard·books…)는 앱 고유 → 앱에 남김. 공용은 래퍼·provider 뼈대만.
3. **소비 = 소스 직접**(vite가 `.jsx` 트랜스파일). web/potato가 `@hanjul/ui` import → workspace symlink가 `packages/ui/src`로. **앱 빌드 순서 불필요 → 배포 리스크 0.**
4. **design-sync용 lib 빌드는 별도** — `packages/ui`에 `build`(esbuild lib→`dist/` + `tsc --allowJs --declaration`→`.d.ts`). **로컬 design-sync 전용, 앱 배포와 무관.** pkg=`@hanjul/ui`면 `node_modules/@hanjul/ui`가 symlink로 존재 → 컨버터가 정식 경로(synth 아님)로 읽음.
5. **theme union 병합** — web∪potato 토큰 하나로. 앱 전용 토큰(sidebar 등)도 다 포함(무해).

## 리스크 & 완화 (놓치면 안 되는 것)
| # | 리스크 | 완화 |
|---|---|---|
| R1 | web theme import **34개**·potato 9개 경로 변경 부담 | **re-export 스텁** — `web/src/theme.js` = `export * from '@hanjul/ui/theme'`. 34개 파일 안 건드림(무중단). 점진 교체는 후속. |
| R2 | **Cloudflare Pages 배포 + workspace** | **둘 다 로컬 빌드+direct upload**라 CF가 workspace 몰라도 무관. (git 자동배포 켜면 재검토) |
| R3 | vitest가 `@hanjul/ui` 못 풀 수도 | workspace symlink + vite resolve로 해결. **각 단계 테스트로 검증**(현 web 113 기준선). |
| R4 | potato `ui.jsx`의 Icon | Icon은 potato에 남기고, 공용 컴포넌트만 `@hanjul/ui` re-export. |
| R5 | theme 토큰 이름충돌(같은 키 다른 값) | **대조 완료**: 브랜드·의미색 전부 동일. drift만 존재 — border/borderSoft/textSoft/faint(1 hex 차, 안 보임), radius(web `sm8/md10/lg14/xl20/hero30` vs potato `sm10/md11/lg13/card18`). **통일** = web 값 기준 + radius는 union(`sm8·md10·lg14·xl20·hero30·card18·pill`). 시각영향 1-2px(무실질). 의도된 차이 아님. |

## 마이그레이션 단계 (각 커밋 + 테스트 green)
1. **루트 workspace + `packages/ui` 스캐폴드** — 루트 `package.json`(workspaces), `packages/ui/package.json`(name·exports·build), `.gitignore`.
2. **theme union** → `packages/ui/src/theme.js` (web∪potato, 값대조). `coverGradient` 포함.
3. **컴포넌트 이동** — `web/src/components/ui/*.jsx` → `packages/ui/src/`. `ui.test.jsx`도 이동(패키지 자체 테스트).
4. **web 무중단 배선** — `web/src/theme.js`·`components/ui/index.js`를 `@hanjul/ui` re-export 스텁으로. `npm install`(symlink) → **web vitest 113 통과 확인**.
5. **potato 무중단 배선** — `potato/src/theme.js`·`ui.jsx`(컴포넌트 부분)를 `@hanjul/ui` re-export, Icon만 남김. **potato build 통과 확인.**
6. **lib 빌드 + dts** — `packages/ui` esbuild+tsc. `dist/index.js` + `*.d.ts` 생성 검증.
7. **design-sync** — config를 `@hanjul/ui`(dist) 가리키게 수정 → 컨버터 build→validate→sync.
8. **(후속·선택)** 앱 import를 `@hanjul/ui`로 직접 교체하고 스텁 제거 (점진).

## design-sync 관점 (왜 이게 정식 경로인가)
- pkg=`@hanjul/ui` → `node_modules/@hanjul/ui/package.json` 존재(workspace symlink) → 컨버터 `projectFor` 통과(이전 `ENOENT` 해결).
- `dist/` 엔트리 + `.d.ts` tree → synth-entry 아닌 **정식 dist 경로**. 타입 계약 정확(dtsPropsFor 불필요, JSDoc→dts 자동).
- 재sync = `packages/ui` 빌드 + `/design-sync` 한 번. 컴포넌트 추가해도 매끄러움.

## 확정 전 확인 필요 (실행 중)
- theme 병합 시 web/potato **동일 키 값 대조**(R5) — 다르면 어떻게 통일할지.
- potato가 CF **git 자동배포**로 전환될 계획 있으면 R2 재설계(workspace-aware 빌드).
