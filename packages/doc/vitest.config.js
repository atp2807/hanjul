// vitest 설정 — dialect/measure/paginate 테스트가 DOMParser/document를 전제하므로 jsdom.
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.js'],
  },
});
