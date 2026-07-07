// DocEditor — mountEditor(코어)의 얇은 React 래퍼.
//
// ⚠️ DOM-as-state: 에디터는 contenteditable DOM 이 곧 정본 상태다. React 가 내용을
//    리렌더하면 커서/입력이 날아간다. 그래서:
//      - 컨테이너 ref 에 1회만 마운트한다(useEffect 의존성 []).
//      - html/apiBase 는 최초 마운트 시점 값만 쓴다(문서 전환은 부모가 key 로 재마운트).
//      - onSave/onUploadMedia/onDirty/onStatus 콜백은 ref 로 최신값을 참조(재-init 없이).
//      - StrictMode 이중 마운트는 destroy 가 멱등(el 비우고 리스너 해제)이라 안전.
//    컨트롤러(save 등)는 controlRef prop 으로 부모에 노출(읽기 전환 전 save 호출용).
import { useEffect, useRef } from 'react';
import { mountEditor } from './editor.js';
import './doc.css';

/**
 * @param {object} props
 * @param {string} props.html 정본 HTML (article[data-juldoc]) — 최초 마운트 값만 사용.
 * @param {string} [props.apiBase] 이미지 표시경로 매핑 베이스 (미지정=passthrough).
 * @param {(html:string)=>any} [props.onSave] 저장 콜백(정본 outerHTML). packages/doc 은 fetch 를 모른다.
 * @param {(file:File)=>Promise<object>} [props.onUploadMedia] 이미지 업로드 콜백.
 * @param {(dirty:boolean)=>void} [props.onDirty]
 * @param {(state:string, err?:Error)=>void} [props.onStatus]
 * @param {import('react').MutableRefObject<any>} [props.controlRef] 코어 컨트롤러 노출용 ref.
 * @param {import('react').CSSProperties} [props.style]
 */
export function DocEditor({ html, apiBase, onSave, onUploadMedia, onDirty, onStatus, controlRef, style }) {
  const ref = useRef(null);
  // 콜백을 ref 로 잡아 최신값을 마운트-1회 클로저에서 참조(콜백 변경이 재-init 을 일으키지 않게).
  const cb = useRef({});
  cb.current = { onSave, onUploadMedia, onDirty, onStatus };

  useEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    const ctrl = mountEditor(el, {
      html,
      apiBase,
      onSave: (outer) => cb.current.onSave?.(outer),
      onUploadMedia: (file) => cb.current.onUploadMedia?.(file),
      onDirty: (dirty) => cb.current.onDirty?.(dirty),
      onStatus: (state, err) => cb.current.onStatus?.(state, err),
    });
    if (controlRef) controlRef.current = ctrl;
    return () => {
      ctrl.destroy();
      if (controlRef) controlRef.current = null;
    };
    // 마운트 1회 — html/apiBase 는 초기값만(DOM-as-state). 문서 전환은 부모가 key 로 재마운트.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return <div ref={ref} style={style} />;
}
