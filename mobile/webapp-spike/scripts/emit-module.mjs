#!/usr/bin/env node
// dist/editor.html (vite-plugin-singlefile 로 CSS/JS 전부 인라인된 단일 파일)을 읽어
// RN 쪽에서 import 가능한 JS 문자열 모듈(mobile/src/editorHtml.js)로 변환한다.
// 실행 순서: "npm run build" (vite build → dist/editor.html) 다음 "npm run emit"
// (또는 한번에 "npm run build:module").
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const here = path.dirname(fileURLToPath(import.meta.url));
const distHtmlPath = path.join(here, '..', 'dist', 'editor.html');
const outPath = path.join(here, '..', '..', 'src', 'editorHtml.js');

if (!existsSync(distHtmlPath)) {
  console.error(
    `[emit-module] dist/editor.html 이 없습니다 — 먼저 "npm run build" 를 실행하세요: ${distHtmlPath}`,
  );
  process.exit(1);
}

const html = readFileSync(distHtmlPath, 'utf8');

// 단일파일 검증 — src=/href= 로 외부 asset 을 참조하는 게 하나라도 남아있으면, RN WebView 에
// html 문자열 하나로 주입했을 때(파일시스템 baseURL 없음) 그 asset 은 반드시 깨진다.
// data: (인라인 base64), http(s): (외부 CDN — 허용), #(문서 내부 앵커)는 예외.
const externalRefPattern = /(?:src|href)\s*=\s*["'](?!data:|https?:\/\/|#)([^"']+)["']/gi;
const leaks = [...html.matchAll(externalRefPattern)].map((m) => m[1]);
if (leaks.length > 0) {
  console.error('[emit-module] 단일파일 검증 실패 — 외부 asset 참조가 남아있습니다:', leaks);
  process.exit(1);
}

// JS 문자열 리터럴로 안전하게 임베드 — 인라인된 번들 코드 안에 백틱/${}/이스케이프가 섞여
//있어도(트랜스파일된 template literal 등) JSON.stringify 가 전부 올바르게 이스케이프하므로,
// 수동 백틱 템플릿 리터럴보다 안전하다(원본 코드에 백틱이 있으면 그쪽이 깨질 수 있음).
const moduleSource = `// AUTO-GENERATED — mobile/webapp-spike 에서 "npm run build:module" 로 생성.
// 원본: mobile/webapp-spike/dist/editor.html (직접 수정 금지 — webapp-spike 소스를 고쳐 재생성할 것)
export const EDITOR_HTML = ${JSON.stringify(html)};
`;

mkdirSync(path.dirname(outPath), { recursive: true });
writeFileSync(outPath, moduleSource, 'utf8');
console.log(
  `[emit-module] ${outPath} 생성 완료 (html ${html.length} chars, external refs ${leaks.length}건)`,
);
