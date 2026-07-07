#!/usr/bin/env node
// Playwright JSON 리포터(`['json', { outputFile }]`) 결과에서 느린 테스트 top N을
// GitHub Actions step summary에 표로 남긴다.
// 필드명은 실제 리포터 출력을 로컬 덤프해 확인한 것 — 문서 추측 아님:
//   suites[].specs[] (재귀: suites[].suites[]도 존재, describe 블록만큼 중첩)
//   spec.tests[].results[] — results[].duration(ms), 재시도마다 하나씩 누적
//   spec.tests[].status — 'expected' | 'unexpected' | 'flaky' | 'skipped'
//
// 사용법: node .github/scripts/pw-slow-tests.mjs <test-results.json 경로> [top N]
import { readFileSync, appendFileSync } from 'node:fs';

const inputPath = process.argv[2] ?? 'web/test-results.json';
const topN = Number(process.argv[3] ?? 10);
const summaryPath = process.env.GITHUB_STEP_SUMMARY;

function writeSummary(md) {
  if (summaryPath) {
    appendFileSync(summaryPath, md);
  } else {
    process.stdout.write(md);
  }
}

let raw;
try {
  raw = readFileSync(inputPath, 'utf-8');
} catch {
  // 테스트가 시작도 못 하고 잡이 실패한 경우 등 — 파일이 없을 수 있다. 잡을 실패시키지 않는다.
  writeSummary(`\n### 느린 테스트 Top ${topN}\n\n_${inputPath} 없음 — 테스트가 리포트를 생성하기 전에 중단된 것으로 보임._\n`);
  process.exit(0);
}

const data = JSON.parse(raw);

// suites는 파일 단위, describe 블록마다 중첩된 suites를 또 가진다 — 재귀 평탄화.
function collectSpecs(suite, out) {
  for (const spec of suite.specs ?? []) {
    for (const test of spec.tests ?? []) {
      const results = test.results ?? [];
      const durationMs = results.reduce((sum, r) => sum + (r.duration ?? 0), 0);
      out.push({
        title: spec.title,
        file: spec.file,
        line: spec.line,
        status: test.status ?? 'unknown', // expected | unexpected | flaky | skipped
        retries: Math.max(results.length - 1, 0),
        durationMs,
      });
    }
  }
  for (const child of suite.suites ?? []) {
    collectSpecs(child, out);
  }
}

const flat = [];
for (const suite of data.suites ?? []) {
  collectSpecs(suite, flat);
}

flat.sort((a, b) => b.durationMs - a.durationMs);
const top = flat.slice(0, topN);

const statusEmoji = { expected: '✅', unexpected: '❌', flaky: '⚠️', skipped: '⏭️' };
const fmtMs = (ms) => `${(ms / 1000).toFixed(1)}s`;

let md = `\n### 느린 테스트 Top ${Math.min(topN, top.length)}\n\n`;
if (data.stats) {
  const s = data.stats;
  md += `전체 ${fmtMs(s.duration ?? 0)} · 성공 ${s.expected ?? 0} · 실패 ${s.unexpected ?? 0} · flaky ${s.flaky ?? 0} · 스킵 ${s.skipped ?? 0}\n\n`;
}
if (top.length === 0) {
  md += '_테스트 결과 없음._\n';
} else {
  md += '| # | 소요시간 | 상태 | 재시도 | 테스트 |\n|---|---|---|---|---|\n';
  top.forEach((t, i) => {
    const emoji = statusEmoji[t.status] ?? t.status;
    md += `| ${i + 1} | ${fmtMs(t.durationMs)} | ${emoji} | ${t.retries} | \`${t.file}:${t.line}\` ${t.title} |\n`;
  });
}

writeSummary(md);
process.stdout.write(md);
