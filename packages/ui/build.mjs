// @hanjul/ui 라이브러리 빌드 — design-sync(claude.ai 디자인 시스템)용 dist 생성.
// 앱(web·potato)은 소스를 직접 소비하므로 이 빌드는 design-sync 전용.
import { build } from 'esbuild';
import { execSync } from 'node:child_process';
import { rmSync } from 'node:fs';

rmSync('./dist', { recursive: true, force: true });

// 1) ESM 번들 (react는 외부 — 소비 측이 제공)
await build({
  entryPoints: ['./src/index.js'],
  outfile: './dist/index.js',
  bundle: true,
  format: 'esm',
  jsx: 'automatic',
  external: ['react', 'react-dom', 'react/jsx-runtime'],
  loader: { '.js': 'jsx' },
  logLevel: 'info',
});

// 2) JSDoc → .d.ts (TypeScript 코드 0 — tsc가 JSDoc만 읽어 타입 선언 생성)
execSync('npx tsc -p tsconfig.build.json', { stdio: 'inherit' });

console.log('✅ @hanjul/ui dist 빌드 완료');
