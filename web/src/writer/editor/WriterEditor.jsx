// 로컬우선 에디터 — ProseMirror + Yjs + y-indexeddb.
// 타이핑 핫패스 = 메모리 Y.Doc(즉시) → y-indexeddb 가 매 변경 로컬 영속(안 날아감).
// 저장 상태를 눈에 보이게 표시 + 마크다운 입력룰(#,##,>) + 문서변경 콜백(자동 목차용).
import { baseKeymap, toggleMark } from 'prosemirror-commands';
import { InputRule, inputRules, textblockTypeInputRule } from 'prosemirror-inputrules';
import { keymap } from 'prosemirror-keymap';
import { EditorState } from 'prosemirror-state';
import { EditorView } from 'prosemirror-view';
import { useEffect, useRef, useState } from 'react';
import { ySyncPlugin, yUndoPlugin, redo as yRedo, undo as yUndo } from 'y-prosemirror';
import { IndexeddbPersistence } from 'y-indexeddb';
import { WebsocketProvider } from 'y-websocket';
import * as Y from 'yjs';

import 'prosemirror-view/style/prosemirror.css';
import './writer.css';
import { schema } from './schema';

// 마커 규칙: 해시 많을수록 큰 단위 (### 챕터 > ## 장 > # 절). 흔한 #은 작은 단위,
// 드문 ###은 중요한 챕터 경계 → 실수 방지. level = 4 - 해시수 (h1=챕터).
function markdownInputRules() {
  return inputRules({
    rules: [
      textblockTypeInputRule(/^(#{1,3})\s$/, schema.nodes.heading, (m) => ({ level: 4 - m[1].length })),
      // blockquote 는 이 스키마에서 textblock(inline*) → wrapping 이 아니라 textblockType 로 변환.
      textblockTypeInputRule(/^\s*>\s$/, schema.nodes.blockquote),
      // 구분선: 줄 처음에서 ---/***/___ → 수평선(hr). 정본·백엔드 import 와 동일 토큰.
      new InputRule(/^(?:---|\*\*\*|___)$/, (state, _match, start, end) =>
        state.tr.replaceRangeWith(start, end, schema.nodes.horizontal_rule.create()),
      ),
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
  const viewRef = useRef(null);
  const [status, setStatus] = useState('loading'); // loading | saving | saved
  const [savedAt, setSavedAt] = useState(null);
  const [synced, setSynced] = useState(false); // 서버 동기화 연결 여부

  useEffect(() => {
    const ydoc = new Y.Doc();
    const persistence = new IndexeddbPersistence(`hanjul-writer-${docId}`, ydoc);
    const yXml = ydoc.getXmlFragment('prosemirror');

    persistence.whenSynced.then(() => setStatus('saved'));

    // 백그라운드 서버 동기화 (SyncPort 웹 어댑터). URL 미설정 시 로컬 단독(오프라인 우선).
    let wsProvider = null;
    const syncUrl = import.meta.env.VITE_SYNC_URL;
    if (syncUrl) {
      wsProvider = new WebsocketProvider(syncUrl, docId, ydoc); // 룸 = docId
      wsProvider.on('status', (e) => setSynced(e.status === 'connected'));
    }

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

    viewRef.current = view;
    onReady?.({ ydoc, view, persistence });
    onChange?.(view.state.doc); // 초기/복원 목차

    return () => {
      clearTimeout(timer);
      ydoc.off('update', onUpdate);
      view.destroy();
      wsProvider?.destroy();
      persistence.destroy();
      ydoc.destroy();
      viewRef.current = null;
    };
  }, [docId]);

  // 툴바: 마크다운 몰라도 클릭으로 블록/서식 지정 (현재 줄/선택에 적용)
  const run = (command) => () => {
    const v = viewRef.current;
    if (!v) return;
    command(v.state, v.dispatch, v);
    v.focus();
  };

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
      <div className="writer-toolbar" data-testid="writer-toolbar">
        <span style={{ fontSize: 12, color: '#9ca3af' }}>
          <code>###</code> 챕터 · <code>##</code> 장 · <code>#</code> 절
        </span>
        <span className="sep" />
        <button type="button" onMouseDown={(e) => e.preventDefault()} onClick={run(toggleMark(schema.marks.strong))}>
          굵게
        </button>
        <button type="button" onMouseDown={(e) => e.preventDefault()} onClick={run(toggleMark(schema.marks.em))}>
          기울임
        </button>
      </div>
      <div className={`writer-status is-${status}`} data-testid="writer-status">
        <span className="dot" />
        {label}
        <span style={{ color: synced ? '#16a34a' : '#cbd5e1' }}>
          {synced ? '· 동기화됨(여러 기기)' : '· 오프라인·새로고침에도 안전'}
        </span>
      </div>
      <div ref={mount} className="writer-pm" data-testid="writer-pm" />
    </div>
  );
}
