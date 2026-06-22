// 로컬우선 글쓰기 페이지 — 자동 목차 사이드바 + 에디터.
// 작가는 파일/챕터를 "관리"하지 않는다: 제목(# )만 쓰면 목차가 자동 생성·점프.
import { TextSelection } from 'prosemirror-state';
import { useCallback, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';

import { docToOutline } from '../writer/core/outline';
import { WriterEditor } from '../writer/editor/WriterEditor';

export function WritePage() {
  const { id } = useParams();
  const [outline, setOutline] = useState([]);
  const viewRef = useRef(null);

  const handleChange = useCallback((doc) => setOutline(docToOutline(doc)), []);
  const handleReady = useCallback(({ view }) => {
    viewRef.current = view;
  }, []);

  function jump(pos) {
    const view = viewRef.current;
    if (!view) return;
    view.focus();
    const sel = TextSelection.near(view.state.doc.resolve(pos + 1));
    view.dispatch(view.state.tr.setSelection(sel).scrollIntoView());
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <aside
        style={{
          width: 240,
          flexShrink: 0,
          padding: '28px 16px',
          borderRight: '1px solid #f0f0f0',
          position: 'sticky',
          top: 0,
          alignSelf: 'flex-start',
          height: '100vh',
          overflowY: 'auto',
          boxSizing: 'border-box',
        }}
      >
        <div style={{ fontSize: 12, color: '#9ca3af', marginBottom: 10 }}>목차 (자동)</div>
        {outline.length === 0 ? (
          <p style={{ fontSize: 13, color: '#cbd5e1', lineHeight: 1.6 }}>
            제목(<code>#&nbsp;</code> 입력)을 넣으면 목차가 자동으로 생겨요.
          </p>
        ) : (
          <ul data-testid="outline" style={{ listStyle: 'none', padding: 0, margin: 0 }}>
            {outline.map((h) => (
              <li key={h.id}>
                <button
                  onClick={() => jump(h.pos)}
                  style={{
                    width: '100%',
                    display: 'flex',
                    justifyContent: 'space-between',
                    gap: 8,
                    border: 'none',
                    background: 'none',
                    cursor: 'pointer',
                    textAlign: 'left',
                    padding: '5px 6px',
                    paddingLeft: 6 + (h.level - 1) * 12,
                    borderRadius: 6,
                    fontSize: 14,
                    color: '#333',
                  }}
                >
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{h.text}</span>
                  <span style={{ color: '#cbd5e1', fontSize: 12, flexShrink: 0 }}>{h.charCount.toLocaleString()}자</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </aside>
      <main style={{ flex: 1, padding: '28px 24px' }}>
        <div style={{ maxWidth: 720, margin: '0 auto' }}>
          <WriterEditor docId={id} onReady={handleReady} onChange={handleChange} />
        </div>
      </main>
    </div>
  );
}
