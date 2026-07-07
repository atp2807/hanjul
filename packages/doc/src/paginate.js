// 줄 단위 페이지네이션 (순수 함수). 긴 블록을 페이지 경계에서 줄 단위로 쪼갠다.
// hanjul/web/src/reader/paginateLines.js 계승 — 로직 확장(표 행 단위 분할 + 인라인 런).
//
// measureLines(block) 반환 형태(3종):
//   1) 텍스트: { lineHeight, marginBottom, lines: string[], richLines?: {runs}[] }
//        richLines[i] 는 lines[i] 와 1:1 — 인라인 굵기 런(strong/em). 있으면 병행 분할.
//   2) 고정:   { fixedHeight, marginBottom, lines: [] }  (img / 근사 표 / 목록)
//   3) 표:     { table:true, splittable, marginBottom, headerRows[], rows[] }
//        row = { height, cells } — splittable 이면 행 단위 분할(헤더행 각 페이지 반복).
//
// 반환: pages = [[fragment, ...], ...]
//   fragment = { blockId, type, lines: string[], richLines?, table? }

/**
 * @param {{id:string, type:string}[]} blocks
 * @param {{contentHeight:number, measureLines:Function}} opts
 * @returns {object[][]}
 */
export function paginateLines(blocks, { contentHeight, measureLines }) {
  const pages = [];
  let current = [];
  let used = 0;

  const breakPage = () => {
    pages.push(current);
    current = [];
    used = 0;
  };

  for (const block of blocks) {
    const m = measureLines(block);

    // ── 표: 실측 행 모델 (병합 표는 통짜, 단순 표는 행 단위 분할) ──────
    if (m.table) {
      const headerHeight = m.headerRows.reduce((s, r) => s + r.height, 0);

      if (!m.splittable) {
        // 병합(colspan/rowspan) 표: 행 분할 금지 — 통짜 배치.
        const tableHeight = headerHeight + m.rows.reduce((s, r) => s + r.height, 0);
        if (used + tableHeight > contentHeight && current.length > 0) breakPage();
        current.push({
          blockId: block.id,
          type: 'TABLE',
          lines: [],
          table: { splittable: false, headerRows: m.headerRows, rows: m.rows },
        });
        used += tableHeight;
        if (tableHeight > contentHeight) {
          // 페이지보다 큰 병합 표 — 분할 불가라 잘림 감수(로그).
          console.warn(
            `[paginate] 병합 표(${block.id})가 페이지 높이(${contentHeight}px)를 초과(${Math.round(tableHeight)}px) — 통짜 유지, 잘림 감수.`,
          );
        }
        used += m.marginBottom;
        continue;
      }

      // 본문행 0개(헤더만 있는 표 / 빈 tbody): while 바디가 안 돌아 fragment 가
      // 안 생겨 표가 통째로 사라졌다(#1). 헤더 fragment 라도 push 해 렌더.
      if (m.rows.length === 0) {
        if (used + headerHeight > contentHeight && current.length > 0) breakPage();
        current.push({
          blockId: block.id,
          type: 'TABLE',
          lines: [],
          table: { splittable: true, headerRows: m.headerRows, rows: [] },
        });
        used += headerHeight + m.marginBottom;
        continue;
      }

      // 병합 없는 단순 표: 남은 공간에 들어가는 행까지, 나머지는 다음 페이지.
      // 헤더행(thead)은 분할된 각 페이지 상단에 반복한다.
      let idx = 0;
      while (idx < m.rows.length) {
        // 헤더만도 안 들어가면 새 페이지.
        if (used + headerHeight > contentHeight && current.length > 0) breakPage();
        used += headerHeight; // 이 페이지에 헤더 반복분 예약
        const chosen = [];
        while (idx < m.rows.length && used + m.rows[idx].height <= contentHeight) {
          used += m.rows[idx].height;
          chosen.push(m.rows[idx]);
          idx++;
        }
        if (chosen.length === 0) {
          // 이 페이지엔 헤더+한 행도 못 넣음.
          if (current.length > 0) {
            used -= headerHeight; // 헤더 예약 취소
            breakPage();
            continue; // 새 페이지에서 재시도
          }
          // 빈 페이지인데도 한 행이 페이지보다 큼 — 강제 배치(잘림 감수, 로그).
          used += m.rows[idx].height;
          chosen.push(m.rows[idx]);
          idx++;
          console.warn(
            `[paginate] 표 행(${block.id})이 페이지 높이를 초과 — 강제 배치, 잘림 감수.`,
          );
        }
        current.push({
          blockId: block.id,
          type: 'TABLE',
          lines: [],
          table: { splittable: true, headerRows: m.headerRows, rows: chosen },
        });
        if (idx < m.rows.length) breakPage(); // 남은 행은 다음 페이지
      }
      used += m.marginBottom;
      continue;
    }

    // ── 고정 높이 / 텍스트 줄 ─────────────────────────────────────────
    const isFixed = m.fixedHeight != null;
    const unitH = isFixed ? m.fixedHeight : m.lineHeight;
    const units = isFixed ? [null] : m.lines; // 고정 높이 = 단위 1개
    const richLines = m.richLines || null;

    let frag = null;
    for (let i = 0; i < units.length; i++) {
      const lineText = units[i];
      if (used + unitH > contentHeight && current.length > 0) {
        breakPage();
        frag = null;
      }
      if (!frag) {
        frag = { blockId: block.id, type: block.type, lines: [] };
        if (richLines) frag.richLines = [];
        current.push(frag);
      }
      if (lineText != null) frag.lines.push(lineText);
      if (richLines && richLines[i]) frag.richLines.push(richLines[i]);
      used += unitH;
    }
    used += m.marginBottom; // 블록 하단 여백 (페이지 분할 강제는 안 함)
  }

  if (current.length > 0) pages.push(current);
  return pages;
}
