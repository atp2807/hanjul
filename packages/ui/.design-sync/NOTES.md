# @hanjul/ui design-sync 노트

## 셋업 (재sync 시 필수)
- shape=**package** (Storybook 없음). synth-entry 아님 — dist 빌드 후 `--entry ./dist/index.js`.
- `buildCmd: npm run build` = esbuild ESM 번들(react external) + `tsc --allowJs --declaration`로
  JSDoc→.d.ts. **TS 코드 0** (JSDoc이 타입 소스).
- 컨버터 실행: `--node-modules ../../node_modules` (루트 — react가 여기 hoisted).
  ⚠️ **react-dom은 sparse hoisting**이라 web에만 있음 → `packages/ui`에 react·react-dom을
  devDep으로 추가해야 루트로 올라옴(이미 되어 있음).
- 렌더검증: playwright **1.61.0**(web과 동일) + chromium-1228. `.ds-sync`에 playwright 설치.
- 앱(web/potato)은 소스(`src/`)를 직접 소비 — 이 dist 빌드는 **design-sync 전용**.

## Known render warns (정상, non-blocking)
- `[CSS_RUNTIME]` — 인라인 스타일 self-styling(CSS-in-JS). 우리 컴포넌트는 CSS 파일 없이
  T 토큰을 인라인 style로 씀. 번들이 self-styling이라 정상.

## Re-sync risks (다음 run이 볼 것)
- `_vendor/react.js`가 1.1MB → `write_files` 시 별도 청크(바이트 제한).
- .d.ts 정확도는 **JSDoc 표준 destructured 형식**(`@param {object} props` + `props.xxx`)에 의존.
  비표준(`@param {type} [kind]`)이면 tsc가 props를 첫 param 타입으로 잘못 추론함 — 새 컴포넌트도 표준 형식으로.
- 컴포넌트 추가 절차: `src/<Name>.jsx`(+표준 JSDoc) → `src/index.js` export → `npm run build`
  → `.design-sync/previews/<Name>.tsx` 저작 → resync.
- `import('react')` 타입은 `@types/react`(devDep) 필요.

## 프로젝트
- claude.ai/design projectId: 687eaa8b-4c05-4623-8318-8771a8d13e4c
- globalName: `HanjulUI` (window.HanjulUI.*)
- 9 컴포넌트: Button·Card·Badge·Chip·Field·PageHeader·Stat·**Avatar·Cover** + theme(T).

## 이력
- **Cover 추가**(2026-07-02, 재sync): 책 표지 표시 프리미티브. web LibraryPage·StorePage의
  로컬 Cover 중복 2개 + BookDetail·Author 인라인 복붙 + 썸네일 4곳(ReviewerActivity·
  CampaignStudio·Moderation)을 통합. `url` 있으면 이미지, 없으면 coverGradient placeholder.
  실표지 업로드가 들어오면 이 한 곳이 이미지로 바뀌는 seam. 5셀 프리뷰 통과.
- **Avatar 추가**(2026-07-02, 재sync): design agent(claude.ai/design)가 우리 토큰으로 디자인 →
  코드로 승격. `f3263907` 프로젝트의 `Avatar.dc.html` 로직 그대로. web·potato 42곳 인라인
  아바타 복붙 정리용. theme에 `AVATAR_GRADIENTS`·`avatarGradient`·`seedHash`(coverGradient와
  공유) 추가 — 표지·아바타 색 동일 해시. resync 드라이버로 Avatar만 added, 8셀 프리뷰 전부 통과.
