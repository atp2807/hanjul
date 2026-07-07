// vitest 설정 — v0 테스트는 순수 로직(챕터 상태순환/재배열)만이라 DOM 불필요, environment: 'node'.
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'node',
    include: ['src/**/*.test.js'],
  },
});
