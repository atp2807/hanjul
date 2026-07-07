import { defineConfig } from 'vite';
import { fileURLToPath } from 'node:url';

// 호스트(pywebview/RN WebView)는 dist/index.html 을 file:// 로 로드한다 — 자산 경로가
// 절대경로(/assets/..)면 깨지므로 base 를 상대경로로 고정한다
// (desktop/webapp/vite.config.js:8 계승 — P0 스파이크에서 실측 확인된 제약).
export default defineConfig({
  root: fileURLToPath(new URL('.', import.meta.url)),
  base: './',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
  server: {
    fs: {
      // packages/doc/src (형제 패키지, package.json exports 밖 경로)를 상대 import 로
      // 그대로 읽기 위함 — mountEditor 는 react 를 끌고 오는 배럴(index.js)을 거치지
      // 않기 위해 일부러 파일 상대경로로 import 한다.
      allow: ['..'],
    },
  },
});
