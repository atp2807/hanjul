#!/usr/bin/env node
// pre-commit 게이트 — staged 파일 중 2MB 초과 파일 차단.
import { execSync } from "node:child_process";
import { statSync } from "node:fs";

const MAX_BYTES = 2 * 1024 * 1024; // 2MB

const output = execSync("git diff --cached --name-only --diff-filter=ACM", {
  encoding: "utf-8",
});
const files = output.split("\n").filter(Boolean);

const offenders = [];
for (const file of files) {
  let size;
  try {
    size = statSync(file).size;
  } catch {
    continue; // 삭제/이동 등으로 stat 실패 시 스킵
  }
  if (size > MAX_BYTES) {
    offenders.push({ file, size });
  }
}

if (offenders.length > 0) {
  console.error("커밋 차단 — 2MB 초과 파일:");
  for (const { file, size } of offenders) {
    console.error(`  ${file} (${(size / 1024 / 1024).toFixed(2)}MB)`);
  }
  process.exit(1);
}
