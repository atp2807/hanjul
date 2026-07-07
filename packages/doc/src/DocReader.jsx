// DocReader — mountReader(코어)의 얇은 React 래퍼.
//
// 리더는 정본 HTML 에서 파생된 순수 뷰라 리렌더(재조판)해도 안전하다. 컨테이너 ref 에
// 마운트하고, html/scale/apiBase 가 바뀌면 재마운트한다. StrictMode 이중 마운트는
// cleanup(destroy)이 멱등이라 안전(마운트→destroy→재마운트).
import { useEffect, useRef } from 'react';
import { mountReader } from './reader.js';
import './doc.css';

/**
 * @param {object} props
 * @param {string} props.html 정본 HTML (article[data-juldoc])
 * @param {number} [props.scale=1]
 * @param {string} [props.pageSize='a4']
 * @param {string} [props.apiBase] 이미지 표시경로 매핑 베이스 (미지정=passthrough)
 * @param {import('react').CSSProperties} [props.style]
 */
export function DocReader({ html, scale = 1, pageSize = 'a4', apiBase, style }) {
  const ref = useRef(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    const ctrl = mountReader(el, { html, scale, pageSize, apiBase });
    return () => ctrl.destroy();
  }, [html, scale, pageSize, apiBase]);

  return <div ref={ref} style={style} />;
}
