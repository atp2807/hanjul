// 로컬우선 에디터 — ProseMirror + Yjs + y-indexeddb.
// 타이핑 핫패스 = 메모리 Y.Doc(즉시) → y-indexeddb 가 매 변경 로컬 영속(안 날아감).
// 저장 상태를 눈에 보이게 표시 + 마크다운 입력룰(#,##,>) + 문서변경 콜백(자동 목차용).
import { baseKeymap, toggleMark } from 'prosemirror-commands';
import { inputRules, textblockTypeInputRule, wrappingInputRule } from 'prosemirror-inputrules';
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

// 마크다운식 입력룰: '# '·'## '·'### ' → 헤딩, '> ' → 인용
function markdownInputRules() {
  return inputRules({
    rules: [
      textblockTypeInputRule(/^(#{1,3})\s$/, schema.nodes.heading, (m) => ({ level: m[1].length })),
      wrappingInputRule(/^\s*>\s$/, schema.nodes.blockquote),
    ],
  });
}

// 제목 끝에서 Enter → 다음 줄은 본문(문단)으로 (제목이 계속 이어지지 않게)
function headingEnter(state, dispatch) {
  const { $from } = state.selection;
  if ($from.parent.type !== schema.nodes.heading) return false;
  if ($from.parentOffset !== $from.parent.content.size) return false; // 끝에서만
  if (dispatch) dispatch(state.tr.split($from.pos, 1, [{ type: schema.nodes.paragraph }]).scrollIntoView());
  return true;
}

export function WriterEditor({ docId, onReady, onChange }) {
  const mount = useRef(null);
  const [status, setStatus] = useState('loading'); // loading | saving | saved
  const [savedAt, setSavedAt] = useState(null);

  useEffect(() => {
    const ydoc = new Y.Doc();
    const persistence = new IndexeddbPersistence(`hanjul-writer-${docId}`, ydoc);
    const yXml = ydoc.getXmlFragment('prosemirror');

    persistence.whenSynced.then(() => setStatus('saved'));

    // 사용자 편집마다 저장상태 갱신 (y-indexeddb 가 매 update 영속 = saved 가 로컬 확정)
    let timer;
    const onUpdate = (_u, origin) => {
      if (origin === persistence) return;
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
        markdownInputRules(),
        keymap({
          Enter: headingEnter,
          'Mod-z': yUndo,
          'Mod-y': yRedo,
          'Mod-Shift-z': yRedo,
          'Mod-b': toggleMark(schema.marks.strong),
          'Mod-i': toggleMark(schema.marks.em),
        }),
        keymap(baseKeymap),
      ],
    });

    const view = new EditorView(mount.current, {
      state,
      // this = view (PM 이 view 로 호출) → const TDZ 회피
      dispatchTransaction(tr) {
        const next = this.state.apply(tr);
        this.updateState(next);
        if (tr.docChanged) onChange?.(next.doc); // 자동 목차 갱신
      },
    });

    onReady?.({ ydoc, view, persistence });
    onChange?.(view.state.doc); // 초기/복원 목차

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
