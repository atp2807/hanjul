import { useMemo, useState } from 'react';

import { paginateLines } from './paginateLines';
import { createPretextLineMeasurer } from './pretextLineMeasurer';
import { blockStyle, READER_STYLE } from './readerStyle';

const TAG_BY_TYPE = { P: 'p', H1: 'h1', H2: 'h2', H3: 'h3', QUOTE: 'blockquote' };

// 한 페이지 분량의 블록 조각(fragment) 렌더. 텍스트는 React 노드로 넣어 자동 escape.
// 측정과 동일한 폰트/너비를 쓰므로 같은 줄로 다시 흐른다(측정==렌더).
function Fragment({ frag, scale }) {
  const st = blockStyle(frag.type);
  const marginBottom = `${st.marginBottom * scale}px`;

  if (frag.type === 'HR') return <hr style={{ marginBottom }} />;

  const Tag = TAG_BY_TYPE[frag.type] || 'p';
  return (
    <Tag
      style={{
        margin: 0,
        marginBottom,
        fontFamily: READER_STYLE.fontFamily,
        fontSize: `${st.fontPx * scale}px`,
        lineHeight: `${st.lineHeight * scale}px`,
        fontWeight: st.weight,
      }}
    >
      {frag.lines.join(' ')}
    </Tag>
  );
}

export function Reader({ blocks }) {
  const [scale, setScale] = useState(1);
  const [pageIdx, setPageIdx] = useState(0);

  const { page, fontFamily } = READER_STYLE;
  const contentWidth = page.width - page.padding * 2;
  const contentHeight = page.height - page.padding * 2;

  // 폰트 배율이 바뀌면 즉시 재조판 (줄 단위 재분할) — Pretext 강점.
  const pages = useMemo(() => {
    const measureLines = createPretextLineMeasurer({ contentWidth, scale });
    return paginateLines(blocks, { contentHeight, measureLines });
  }, [blocks, scale, contentWidth, contentHeight]);

  const idx = Math.min(pageIdx, Math.max(0, pages.length - 1));
  const currentFrags = pages[idx] || [];

  return (
    <div style={{ fontFamily }}>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12, alignItems: 'center' }}>
        <button onClick={() => setScale((s) => Math.max(0.7, +(s - 0.1).toFixed(2)))}>A-</button>
        <button onClick={() => setScale((s) => Math.min(2, +(s + 0.1).toFixed(2)))}>A+</button>
        <span>배율 {scale.toFixed(1)}x</span>
        <span style={{ marginLeft: 'auto' }}>
          {pages.length ? idx + 1 : 0} / {pages.length}
        </span>
      </div>

      <div
        style={{
          width: page.width,
          height: page.height,
          padding: page.padding,
          boxSizing: 'border-box',
          border: '1px solid #ddd',
          borderRadius: 8,
          overflow: 'hidden',
          background: '#fff',
        }}
      >
        {currentFrags.map((frag, i) => (
          <Fragment key={`${frag.blockId}#${i}`} frag={frag} scale={scale} />
        ))}
      </div>

      <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
        <button disabled={idx <= 0} onClick={() => setPageIdx(idx - 1)}>
          ← 이전
        </button>
        <button disabled={idx >= pages.length - 1} onClick={() => setPageIdx(idx + 1)}>
          다음 →
        </button>
      </div>
    </div>
  );
}
