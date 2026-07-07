import { defineConfig } from 'vite';
import { fileURLToPath } from 'node:url';
import { viteSingleFile } from 'vite-plugin-singlefile';

// RN <WebView source={{ html: EDITOR_HTML }}> 는 문자열 하나로 페이지를 주입한다 — 외부
// <script src>/<link href>/CSS background 참조가 하나라도 남으면 WebView 안에서 상대경로
// asset 로딩이 깨진다(파일시스템 baseURL 이 없음). 그래서 vite-plugin-singlefile 로 JS/CSS 를
// 전부 base64/inline 으로 접어 editor.html 하나만 산출한다(emit-module.mjs 가 이 단일파일을
// 검증 후 JS 문자열 모듈로 변환).
export default defineConfig({
  root: fileURLToPath(new URL('.', import.meta.url)),
  base: './',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    cssCodeSplit: false,
    assetsInlineLimit: 100000000, // 안전망 — singlefile 플러그인과 같은 취지로 전부 인라인.
    rollupOptions: {
      input: fileURLToPath(new URL('./editor.html', import.meta.url)),
    },
  },
  plugins: [viteSingleFile()],
  server: {
    fs: {
      // packages/doc/src (모노레포 루트 바깥 경로)를 상대 import 로 그대로 읽기 위함.
      allow: ['../..'],
    },
  },
});
