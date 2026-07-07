// theme.js — @hanjul/ui 디자인 토큰(packages/ui/src/theme.js:4-42 의 `T`)을
// ide-core 전용 CSS 커스텀 프로퍼티(--hj-*)로 변환한다.
//
// ide-core 는 React 비의존(package.json 설명 참조)이라 @hanjul/ui 의 React 컴포넌트는
// 쓰지 않는다 — `@hanjul/ui/theme` 는 packages/ui/package.json:8 의 별도 export 경로라
// index.js(React 컴포넌트 배럴)를 거치지 않고 순수 데이터(T 객체)만 가져온다.
//
// style.css 는 하드코딩 hex 대신 이 변수들을 참조한다(예: background: var(--hj-ink)).
// 토큰 자체를 바꾸고 싶으면 packages/ui/src/theme.js 의 T 를 고치면 여기 재빌드 없이
// (런타임 import 이므로) 다음 로드에 바로 반영된다.
import { T } from '@hanjul/ui/theme';

/** @hanjul/ui T → --hj-* CSS 커스텀 프로퍼티 매핑. 값 자체는 T 를 그대로 참조(드리프트 방지). */
export const THEME_CSS_VARS = {
  '--hj-bg': T.bg,
  '--hj-surface': T.surface,
  '--hj-ink': T.ink,
  '--hj-ink-text': T.inkText,
  '--hj-text-strong': T.textStrong,
  '--hj-text': T.text,
  '--hj-text-soft': T.textSoft,
  '--hj-muted': T.muted,
  '--hj-faint': T.faint,
  '--hj-border': T.border,
  '--hj-border-soft': T.borderSoft,
  '--hj-tint': T.tint,
  '--hj-ok': T.ok,
  '--hj-warn': T.warn,
  '--hj-danger': T.danger,
  '--hj-radius-sm': `${T.radius.sm}px`,
  '--hj-radius-md': `${T.radius.md}px`,
  '--hj-radius-lg': `${T.radius.lg}px`,
  '--hj-font-ui': T.font,
  // 본문(캔버스) 서체 — UI 크롬(--hj-font-ui, 고딕)과 대비되는 명조 계열.
  // Noto Serif KR(번들 woff2, src/assets/fonts) → 시스템 명조 → 고딕(최종 안전망).
  '--hj-font-serif':
    "'Noto Serif KR', 'Nanum Myeongjo', AppleMyungjo, Batang, 'IBM Plex Sans KR', -apple-system, BlinkMacSystemFont, system-ui, sans-serif",
};

/**
 * 문서 루트에 @hanjul/ui 토큰을 CSS 커스텀 프로퍼티로 적용. main.js 가 마운트 전 1회 호출.
 * @param {Document} [doc]
 */
export function applyThemeTokens(doc = document) {
  const root = doc.documentElement;
  for (const [name, value] of Object.entries(THEME_CSS_VARS)) {
    root.style.setProperty(name, String(value));
  }
}
