// 공용 vitest 테스트 설정 조각 — web·potato·packages/* 가 test 블록에 스프레드해서 쓴다.
// coverage 등 앱/패키지별 고유 항목은 각자 vite.config.js/vitest.config.js 에 남기고
// 여기엔 정말 공통인 것만 (환경·전역·셋업파일).
export const sharedTestConfig = {
  environment: 'jsdom',
  globals: true,
  setupFiles: ['@hanjul/test-utils/setup'],
};
