import { defineConfig } from 'vite';

// 조판 e2e 하니스 전용 개발서버 — 빌드 불필요, 정적 서빙 + bare import 해석용.
// root='./e2e' 로 지정해도 @hanjul/doc bare import 는 워크스페이스 심링크
// (node_modules/@hanjul/doc → ../../packages/doc, 리포 루트에서 위쪽 탐색으로 발견)를 통해
// 정상 해석된다 — 실측 확인됨(자기 자신을 가리키는 심링크를 vite 가 실경로로 풀어 src/index.js
// 로 서빙). Playwright webServer 가 이 설정으로 dev 서버를 띄워 하니스 html 만 서빙한다.
export default defineConfig({
  root: './e2e',
  server: {
    // 웰노운/흔한 포트 회피 — 다른 워크스페이스 포트(web 35173/35200, potato 35180)와 미충돌.
    port: parseInt(process.env.VITE_PORT || '35300', 10),
    strictPort: true,
  },
});
