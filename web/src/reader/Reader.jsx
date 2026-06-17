import { useMemo, useState } from 'react';

import { paginate } from './paginate';
import { createPretextMeasurer } from './pretextMeasurer';
import { blockStyle, READER_STYLE } from './readerStyle';

// 한 블록을 정본 HTML 그대로 렌더 — 측정과 동일한 타이포 인라인 적용(측정==렌더).
function BlockView({ block, scale }) {
  const st = blockStyle(block.type);
  const style = {
    fontFamily: READER_STYLE.fontFamily,
    fontSize: `${st.fontPx * scale}px`,
    lineHeight: `${st.lineHeight * scale}px`,
    fontWeight: st.weight,
    marginBottom: `${st.marginBottom * scale}px`,
  };
  return (
    <div
      className="hj-block"
      style={style}
      dangerouslySetInnerHTML={{ __html: block.html }}
    />
  );
}

export function Reader({ blocks }) {
  const [scale, setScale] = useState(1);
  const [pageIdx, setPageIdx] = useState(0);

  const { page, fontFamily } = READER_STYLE;
  const contentWidth = page.width - page.padding * 2;
  const contentHeight = page.height - page.padding * 2;

  // 폰트 배율이 바뀌면 즉시 재조판 — Pretext의 강점.
  const pages = useMemo(() => {
    const measure = createPretextMeasurer({ contentWidth, scale });
    return paginate(blocks, { contentHeight, measure });
  }, [blocks, scale, contentWidth, contentHeight]);

  const idx = Math.min(pageIdx, Math.max(0, pages.length - 1));
  const currentBlocks = pages[idx] || [];

  return (
    <div style={{ fontFamily }}>
      {/* 내부 태그 기본 여백 제거 — 측정값과 렌더 높이 일치 보장 */}
      <style>{`.hj-block > * { margin: 0; }`}</style>

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
        {currentBlocks.map((b) => (
          <BlockView key={b.id} block={b} scale={scale} />
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
