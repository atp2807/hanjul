// 로컬우선 에디터 — ProseMirror + Yjs + y-indexeddb.
// 타이핑 핫패스 = 메모리 Y.Doc(즉시) → y-indexeddb 가 매 변경 로컬 영속(안 날아감).
// 네트워크 동기화(SyncPort)는 다음 증분. 지금은 로컬 단독으로도 완전 동작.
import { baseKeymap, toggleMark } from 'prosemirror-commands';
import { keymap } from 'prosemirror-keymap';
import { EditorState } from 'prosemirror-state';
import { EditorView } from 'prosemirror-view';
import { useEffect, useRef } from 'react';
import { ySyncPlugin, yUndoPlugin, redo as yRedo, undo as yUndo } from 'y-prosemirror';
import { IndexeddbPersistence } from 'y-indexeddb';
import * as Y from 'yjs';

import 'prosemirror-view/style/prosemirror.css';
import './writer.css';
import { schema } from './schema';

export function WriterEditor({ docId, onReady }) {
  const mount = useRef(null);

  useEffect(() => {
    const ydoc = new Y.Doc();
    const persistence = new IndexeddbPersistence(`hanjul-writer-${docId}`, ydoc);
    const yXml = ydoc.getXmlFragment('prosemirror');

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
      view.destroy();
      persistence.destroy();
      ydoc.destroy();
    };
  }, [docId]);

  return <div ref={mount} className="writer-pm" data-testid="writer-pm" />;
}
