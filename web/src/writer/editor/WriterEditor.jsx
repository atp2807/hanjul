// 로컬우선 에디터 — ProseMirror + Yjs + y-indexeddb.
// 타이핑 핫패스 = 메모리 Y.Doc(즉시) → y-indexeddb 가 매 변경 로컬 영속(안 날아감).
// 저장 상태를 눈에 보이게 표시 = "안 날아감"을 체감시키는 핵심 UX.
// 네트워크 동기화(SyncPort)는 다음 증분. 지금은 로컬 단독으로도 완전 동작.
import { baseKeymap, toggleMark } from 'prosemirror-commands';
import { keymap } from 'prosemirror-keymap';
import { EditorState } from 'prosemirror-state';
import { EditorView } from 'prosemirror-view';
import { useEffect, useRef, useState } from 'react';
import { ySyncPlugin, yUndoPlugin, redo as yRedo, undo as yUndo } from 'y-prosemirror';
import { IndexeddbPersistence } from 'y-indexeddb';
import * as Y from 'yjs';

import 'prosemirror-view/style/prosemirror.css';
import './writer.css';
import { schema } from './schema';

export function WriterEditor({ docId, onReady }) {
  const mount = useRef(null);
  const [status, setStatus] = useState('loading'); // loading | saving | saved
  const [savedAt, setSavedAt] = useState(null);

  useEffect(() => {
    const ydoc = new Y.Doc();
    const persistence = new IndexeddbPersistence(`hanjul-writer-${docId}`, ydoc);
    const yXml = ydoc.getXmlFragment('prosemirror');

    // 초기 로컬 로드 완료 → 준비됨(있으면 복원된 상태)
    persistence.whenSynced.then(() => setStatus('saved'));

    // 사용자 편집(origin≠persistence)마다: 저장중 → 짧은 디바운스 후 저장됨.
    // y-indexeddb 가 매 update 를 IndexedDB 에 영속하므로 'saved'=로컬 확정.
    let timer;
    const onUpdate = (_update, origin) => {
      if (origin === persistence) return; // 로드로 인한 변경은 제외
      setStatus('saving');
      clearTimeout(timer);
      timer = setTimeout(() => {
        setSavedAt(Date.now());
        setStatus('saved');
      }, 250);
    };
    ydoc.on('update', onUpdate);

    const state = EditorState.create({
      schema,
      plugins: [
        ySyncPlugin(yXml),
        yUndoPlugin(),
        keymap({
          'Mod-z': yUndo,
          'Mod-y': yRedo,
          'Mod-Shift-z': yRedo,
          'Mod-b': toggleMark(schema.marks.strong),
          'Mod-i': toggleMark(schema.marks.em),
        }),
        keymap(baseKeymap),
      ],
    });

    const view = new EditorView(mount.current, { state });
    onReady?.({ ydoc, view, persistence });

    return () => {
      clearTimeout(timer);
      ydoc.off('update', onUpdate);
      view.destroy();
      persistence.destroy();
      ydoc.destroy();
    };
  }, [docId]);

  const label =
    status === 'loading'
      ? '불러오는 중…'
      : status === 'saving'
        ? '저장 중…'
        : savedAt
          ? `이 기기에 저장됨 · ${new Date(savedAt).toLocaleTimeString()}`
          : '이 기기에 저장됨';

  return (
    <div>
      <div className={`writer-status is-${status}`} data-testid="writer-status">
        <span className="dot" />
        {label}
        <span style={{ color: '#cbd5e1' }}>· 오프라인·새로고침에도 안전</span>
      </div>
      <div ref={mount} className="writer-pm" data-testid="writer-pm" />
    </div>
  );
}
