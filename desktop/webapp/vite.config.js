import { defineConfig } from 'vite';
import { fileURLToPath } from 'node:url';

// pywebview 는 dist/index.html 을 file:// 로 로드한다 — 자산 경로가 절대경로(/assets/..)면
// 깨지므로 base 를 상대경로로 고정한다.
export default defineConfig({
  root: fileURLToPath(new URL('.', import.meta.url)),
  base: './',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
  server: {
    fs: {
      // packages/doc/src (모노레포 루트 바깥 경로)를 상대 import 로 그대로 읽기 위함.
      allow: ['../..'],
    },
  },
});
