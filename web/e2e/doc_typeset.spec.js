// 실제 브라우저(chromium) 조판 검증 — Pretext 실측정 정본.
// juldoc(../../juldoc/web/e2e/typeset.spec.js)에서 이식. vitest(jsdom)는 canvas 가 없어
// 근사/파서만 검증하므로, 표 실측 행 높이·인라인 굵기 줄 수·헤더 반복 같은 "측정 결과"는
// 여기서 실측 assert 한다. assertion 본문은 원본과 동일 — beforeEach 의 하니스 경로만
// hanjul 배치(web/e2e/doc-typeset-harness.html, vite 가 /e2e/... 로 서빙)에 맞춰 바뀌었다.
import { test, expect } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.goto('/e2e/doc-typeset-harness.html');
  await page.waitForFunction('window.__ready === true');
});

// ── (a) 텍스트 블록 줄 수 ────────────────────────────────────────────────
test('문단은 좁은 폭에서 여러 시각적 줄로 줄바꿈된다', async ({ page }) => {
  const lineCount = await page.evaluate(() => {
    const text =
      'The quick brown fox jumps over the lazy dog while the sun sets slowly behind the distant hills';
    const m = window.juldoc.measureBlock('P', text, 240);
    return m.lines.length;
  });
  expect(lineCount).toBeGreaterThan(1);
});

// ── (c) 인라인 굵기가 줄 수에 반영된다 ──────────────────────────────────
test('굵은(strong) 문단은 같은 텍스트의 평문보다 더 많은 줄로 배치되는 폭이 존재한다', async ({ page }) => {
  const result = await page.evaluate(() => {
    const words =
      'lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor incididunt ut labore et dolore magna aliqua enim minim veniam quis nostrud';
    const plainHtml = words;
    const boldHtml = `<strong>${words}</strong>`;
    const observations = [];
    let foundStrictlyMore = false;
    let boldHasRuns = false;
    for (let w = 200; w <= 640; w += 20) {
      const plain = window.juldoc.measureBlock('P', plainHtml, w);
      const bold = window.juldoc.measureBlock('P', boldHtml, w);
      if (bold.richLines && bold.richLines[0].runs[0].bold) boldHasRuns = true;
      observations.push({ w, plain: plain.lines.length, bold: bold.lines.length });
      if (bold.lines.length > plain.lines.length) foundStrictlyMore = true;
      // 굵기가 줄 수를 줄이는 일은 없어야 한다(더 넓으니까).
      if (bold.lines.length < plain.lines.length) return { invalid: { w } };
    }
    return { foundStrictlyMore, boldHasRuns, observations };
  });
  expect(result.invalid).toBeUndefined();
  expect(result.boldHasRuns).toBe(true); // 혼합 굵기 경로(richLines)가 실제로 돌았다
  expect(result.foundStrictlyMore).toBe(true); // 굵기 때문에 줄이 늘어나는 폭이 실재
});

test('평문 경로와 혼합 굵기 경로는 서로 다른 렌더 구조를 낳는다', async ({ page }) => {
  const shape = await page.evaluate(() => {
    const plain = window.juldoc.measureBlock('P', 'hello world here', 400);
    const bold = window.juldoc.measureBlock('P', 'hello <strong>world</strong> here', 400);
    return {
      plainHasRich: !!plain.richLines,
      boldHasRich: !!bold.richLines,
      // 굵기 경로는 런에 서식 정보가 실린다.
      boldRuns: bold.richLines[0].runs.map((r) => ({ text: r.text, bold: r.bold })),
    };
  });
  expect(shape.plainHasRich).toBe(false); // 서식 없으면 keep-all 평문 경로
  expect(shape.boldHasRich).toBe(true);
  // 'world' 만 bold, 나머지는 평문으로 분리 측정됐다.
  const boldWord = shape.boldRuns.find((r) => r.text.trim() === 'world');
  expect(boldWord).toBeTruthy();
  expect(boldWord.bold).toBe(true);
});

// ── (b) 표 행 높이 실측 — 근사(34px 고정)가 아니라 셀 내용에 따라 변한다 ──
test('표 행 높이는 셀 내용(줄 수)에 따라 달라진다 — 고정 34px 아님', async ({ page }) => {
  const rows = await page.evaluate(() => {
    // 2열 표: 한 행은 짧은 셀, 한 행은 폭을 넘겨 여러 줄로 감기는 긴 셀.
    const html =
      '<table><thead><tr><th>Name</th><th>Note</th></tr></thead><tbody>' +
      '<tr><td>A</td><td>short</td></tr>' +
      '<tr><td>B</td><td>This is a considerably longer cell whose text will certainly wrap onto multiple visual lines inside a narrow fixed-width column</td></tr>' +
      '</tbody></table>';
    const m = window.juldoc.measureTable(html, 360);
    return {
      splittable: m.splittable,
      headerH: m.headerRows[0].height,
      shortH: m.rows[0].height,
      longH: m.rows[1].height,
      longCellLines: m.rows[1].cells[1].lines.length,
    };
  });
  expect(rows.splittable).toBe(true);
  // 긴 셀 행이 짧은 셀 행보다 확실히 높다(내용 기반 측정의 증거).
  expect(rows.longCellLines).toBeGreaterThan(1);
  expect(rows.longH).toBeGreaterThan(rows.shortH);
  // 근사값(34px 고정)과 다르다.
  expect(rows.shortH).not.toBe(34);
  expect(rows.longH).not.toBe(34);
});

// ── (b) 표 행 단위 페이지 분할 + 헤더 반복 ──────────────────────────────
test('표는 행 단위로 페이지 분할되고 헤더행이 각 페이지 상단에 반복된다', async ({ page }) => {
  const split = await page.evaluate(() => {
    const html =
      '<table><thead><tr><th>Col A</th><th>Col B</th></tr></thead><tbody>' +
      Array.from({ length: 6 }, (_, i) => `<tr><td>r${i}a</td><td>r${i}b</td></tr>`).join('') +
      '</tbody></table>';
    const model = window.juldoc.measureTable(html, 360);
    // 헤더 + 2행이 한 페이지에 겨우 들어가도록 contentHeight 를 잡는다.
    const headerH = model.headerRows[0].height;
    const rowH = model.rows[0].height;
    const contentHeight = headerH + rowH * 2 + 1;
    const pages = window.juldoc.paginateLines([{ id: 't0', type: 'TABLE' }], {
      contentHeight,
      measureLines: () => model,
    });
    return {
      pageCount: pages.length,
      headerPerPage: pages.map((p) => p.find((f) => f.type === 'TABLE').table.headerRows.length),
      rowsPerPage: pages.map((p) => p.find((f) => f.type === 'TABLE').table.rows.length),
      totalRows: pages.reduce((n, p) => n + p.find((f) => f.type === 'TABLE').table.rows.length, 0),
    };
  });
  expect(split.pageCount).toBeGreaterThan(1);
  // 모든 페이지에 헤더행이 반복된다.
  for (const h of split.headerPerPage) expect(h).toBe(1);
  // 본문 행이 유실 없이 모두 보존된다.
  expect(split.totalRows).toBe(6);
});

test('분할된 표는 실제 DOM 에서 헤더가 페이지마다 반복 렌더된다', async ({ page }) => {
  const dom = await page.evaluate(() => {
    // 페이지보다 훨씬 큰 표(많은 행) → 여러 페이지로 분할.
    const html =
      '<article data-juldoc><table><thead><tr><th>Col A</th><th>Col B</th></tr></thead><tbody>' +
      Array.from({ length: 40 }, (_, i) => `<tr><td>row ${i} a</td><td>row ${i} b</td></tr>`).join('') +
      '</tbody></table></article>';
    const pageCount = window.juldoc.mount(html, { scale: 1, pageSize: 'a4' });
    const stage = document.getElementById('stage');
    return {
      pageCount,
      theadCount: stage.querySelectorAll('table thead').length,
      bodyRowTotal: stage.querySelectorAll('table tbody tr').length,
      // 헤더 셀 텍스트가 여러 번 나타난다.
      headerCells: Array.from(stage.querySelectorAll('table thead th')).map((th) => th.textContent),
    };
  });
  expect(dom.pageCount).toBeGreaterThan(1);
  expect(dom.theadCount).toBeGreaterThan(1); // 헤더 반복
  expect(dom.bodyRowTotal).toBe(40); // 본문 40행 전부 보존
  // 반복된 헤더마다 'Col A'/'Col B'.
  expect(dom.headerCells.filter((t) => t === 'Col A').length).toBe(dom.theadCount);
});

// ── #2 (최우선): <br>/DOCX '\n' 강제개행이 소실되지 않는다 ──────────────
test('문단의 <br> 강제개행이 별도 줄로 보존된다(#2)', async ({ page }) => {
  const r = await page.evaluate(() => {
    const m = window.juldoc.measureBlock('P', 'a<br>b', 400);
    return { count: m.lines.length, lines: m.lines };
  });
  expect(r.count).toBe(2); // 접히면 1
  expect(r.lines).toEqual(['a', 'b']);
});

test("DOCX식 raw '\\n' 텍스트도 별도 줄로 보존된다(#2)", async ({ page }) => {
  const r = await page.evaluate(() => {
    // docx.py 가 w:br 을 텍스트 노드 '\n' 로 넣는 경우 — html 에 raw 개행.
    const m = window.juldoc.measureBlock('P', 'first line\nsecond line', 400);
    return { count: m.lines.length, lines: m.lines };
  });
  expect(r.count).toBe(2);
  expect(r.lines).toEqual(['first line', 'second line']);
});

test('굵기 섞인 강제개행도 줄이 나뉘고 굵기가 보존된다(#2)', async ({ page }) => {
  const r = await page.evaluate(() => {
    const m = window.juldoc.measureBlock('P', 'plain<br><strong>bold</strong>', 400);
    return {
      count: m.lines.length,
      lines: m.lines,
      secondLineBold: m.richLines[1].runs.some((run) => run.bold && run.text.includes('bold')),
    };
  });
  expect(r.count).toBe(2);
  expect(r.lines).toEqual(['plain', 'bold']);
  expect(r.secondLineBold).toBe(true);
});

test('실제 DOM 에서 <br> 문단이 양쪽 텍스트를 모두 렌더한다(#2)', async ({ page }) => {
  const r = await page.evaluate(() => {
    window.juldoc.mount('<article data-juldoc><p>alpha<br><strong>beta</strong></p></article>', {
      scale: 1,
    });
    const stage = document.getElementById('stage');
    const p = stage.querySelector('.juldoc-page p');
    return {
      text: p.textContent, // '\n' 포함(pre-wrap) — 데이터 소실 아님
      hasStrong: !!p.querySelector('strong'),
      strongText: p.querySelector('strong')?.textContent,
    };
  });
  expect(r.text).toBe('alpha\nbeta'); // 둘 다 살아있고 강제개행 유지
  expect(r.hasStrong).toBe(true);
  expect(r.strongText).toBe('beta');
});

// ── #1: 헤더만 있는(본문행 0) 표가 통째로 사라지지 않는다 ────────────────
test('본문행 0개(헤더만) 표도 페이지에 렌더된다 — 데이터 소실 없음(#1)', async ({ page }) => {
  const r = await page.evaluate(() => {
    const html =
      '<article data-juldoc><table><thead><tr><th>Col A</th><th>Col B</th></tr></thead>' +
      '<tbody></tbody></table></article>';
    const pageCount = window.juldoc.mount(html, { scale: 1 });
    const stage = document.getElementById('stage');
    return {
      pageCount,
      theadCount: stage.querySelectorAll('table thead').length,
      headerCells: Array.from(stage.querySelectorAll('table thead th')).map((th) => th.textContent),
    };
  });
  expect(r.pageCount).toBeGreaterThan(0); // 사라지면 0
  expect(r.theadCount).toBeGreaterThan(0); // 헤더가 렌더됨
  expect(r.headerCells).toEqual(['Col A', 'Col B']);
});

// ── #3: 중첩 표의 내부 행이 바깥 표를 오염시키지 않는다(실측정 경로) ────
test('중첩 표를 실측정해도 바깥 표 본문행 수가 정확하다(#3)', async ({ page }) => {
  const r = await page.evaluate(() => {
    const html =
      '<table><thead><tr><th>A</th><th>B</th></tr></thead><tbody>' +
      '<tr><td>1</td><td><table><tbody>' +
      '<tr><td>x</td><td>y</td><td>z</td></tr><tr><td>p</td><td>q</td><td>r</td></tr>' +
      '</tbody></table></td></tr></tbody></table>';
    const m = window.juldoc.measureTable(html, 400);
    return { bodyRows: m.rows.length, headerRows: m.headerRows.length, splittable: m.splittable };
  });
  expect(r.bodyRows).toBe(1); // 내부 2행이 새면 3
  expect(r.headerRows).toBe(1);
  expect(r.splittable).toBe(true);
});

// ── #4: 굵은 셀은 평문 셀보다 넓어 더 많은 줄로 측정된다(측정=렌더 정합) ─
test('굵은(strong) 셀은 같은 텍스트 평문 셀보다 더 감기는 폭이 존재한다(#4)', async ({ page }) => {
  const r = await page.evaluate(() => {
    const words =
      'lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor incididunt';
    const plainHtml = `<table><tbody><tr><td>${words}</td></tr></tbody></table>`;
    const boldHtml = `<table><tbody><tr><td><strong>${words}</strong></td></tr></tbody></table>`;
    let foundStrictlyMore = false;
    let invalid = null;
    for (let w = 240; w <= 640; w += 20) {
      const p = window.juldoc.measureTable(plainHtml, w).rows[0].cells[0].lines.length;
      const b = window.juldoc.measureTable(boldHtml, w).rows[0].cells[0].lines.length;
      if (b < p) invalid = { w, p, b };
      if (b > p) foundStrictlyMore = true;
    }
    return { foundStrictlyMore, invalid };
  });
  expect(r.invalid).toBeNull(); // 굵기가 줄을 줄이는 일은 없다
  expect(r.foundStrictlyMore).toBe(true); // 굵어서 더 감기는 폭이 실재
});

// ── 병합(colspan/rowspan) 표는 행 분할 안 하고 통짜 유지 ──────────────
test('병합(colspan) 표는 splittable=false 이며 통짜로 유지된다', async ({ page }) => {
  const merged = await page.evaluate(() => {
    const html =
      '<table><thead><tr><th colspan="2">Merged Header</th></tr></thead><tbody>' +
      Array.from({ length: 6 }, (_, i) => `<tr><td>r${i}a</td><td>r${i}b</td></tr>`).join('') +
      '</tbody></table>';
    const model = window.juldoc.measureTable(html, 360);
    const headerH = model.headerRows[0].height;
    const rowH = model.rows[0].height;
    const contentHeight = headerH + rowH * 2 + 1; // 통짜론 안 들어가는 높이
    const warnings = [];
    const origWarn = console.warn;
    console.warn = (m) => warnings.push(m);
    const pages = window.juldoc.paginateLines([{ id: 't0', type: 'TABLE' }], {
      contentHeight,
      measureLines: () => model,
    });
    console.warn = origWarn;
    const tableFrags = pages.flat().filter((f) => f.type === 'TABLE');
    return {
      splittable: model.splittable,
      fragCount: tableFrags.length,
      rowsInFrag: tableFrags[0].table.rows.length,
      warned: warnings.length > 0,
    };
  });
  expect(merged.splittable).toBe(false); // 병합 감지
  expect(merged.fragCount).toBe(1); // 행 분할 안 함 — 단일 fragment
  expect(merged.rowsInFrag).toBe(6); // 전 행 한 곳에
  expect(merged.warned).toBe(true); // 페이지 초과 잘림 경고 로그
});
