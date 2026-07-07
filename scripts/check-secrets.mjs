#!/usr/bin/env node
// pre-commit 게이트 — staged 변경분(추가된 라인만)에서 시크릿 패턴 차단.
import { execSync } from "node:child_process";

const PATTERNS = [
  /-----BEGIN[ A-Z]*PRIVATE KEY-----/,
  /AKIA[0-9A-Z]{16}/,
  /postgresql\+asyncpg:\/\/[^:]+:[^@]{4,}@/,
  /sk_live_[0-9a-zA-Z]+/,
  /_SECRET_KEY\s*=\s*['"][^'"]{8,}['"]/,
  // 이 프로젝트 고유 시크릿 접미어(settlement 계좌 암호화 키 등) — _SECRET_KEY 패턴이 못 잡음.
  /_ENC_KEY\s*=\s*['"][^'"]{8,}['"]/,
];

const diff = execSync("git diff --cached -U0", {
  encoding: "utf-8",
  maxBuffer: 1024 * 1024 * 50,
});
const lines = diff.split("\n");

let currentFile = null;
let newLineNo = 0;
const offenders = [];

for (const line of lines) {
  if (line.startsWith("+++ ")) {
    const path = line.slice(4).trim();
    currentFile = path.startsWith("b/") ? path.slice(2) : path;
    continue;
  }
  if (line.startsWith("@@ ")) {
    const m = line.match(/@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@/);
    if (m) newLineNo = parseInt(m[1], 10);
    continue;
  }
  if (line.startsWith("---")) {
    continue;
  }
  if (line.startsWith("+")) {
    const content = line.slice(1);
    if (PATTERNS.some((pattern) => pattern.test(content))) {
      offenders.push(`${currentFile}:${newLineNo} — ${content.trim().slice(0, 100)}`);
    }
    newLineNo++;
    continue;
  }
  if (line.startsWith("-")) {
    continue; // 삭제 라인 — 신규 라인번호 카운터에 영향 없음
  }
}

if (offenders.length > 0) {
  console.error("커밋 차단 — 시크릿 패턴 감지:");
  for (const o of offenders) console.error(`  ${o}`);
  process.exit(1);
}
