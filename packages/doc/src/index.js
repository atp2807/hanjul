// @hanjul/doc — 한줄독(juldoc) 문서 코어 배럴.
//  - 순수 JS 코어: 방언 정규화 · 텍스트 측정 · 페이지 분할 · 미디어 src 매핑.
//  - 프레임워크 무소속 마운트: mountEditor / mountReader (contenteditable / 페이지 조판).
//  - 얇은 React 래퍼: DocEditor / DocReader (ref 마운트, DOM-as-state).
export { ALLOWED_BLOCKS, ALLOWED_INLINE, sanitizeUrl, normalizeFragment, normalizeHtml } from './dialect.js';
export {
  PAGE_SIZES,
  blockStyle,
  scaledStyle,
  scaledTableCell,
  parseInlineSegments,
  parseTableModel,
  createMeasurer,
} from './measure.js';
export { paginateLines } from './paginate.js';
export { mediaSrcToDisplay, mediaSrcToCanonical, mapImgSrcs } from './media.js';
export {
  mountEditor,
  createTable,
  computeScaledSize,
  downscaleImage,
  MAX_UPLOAD_SIDE,
} from './editor.js';
export { mountReader } from './reader.js';
export { DocEditor } from './DocEditor.jsx';
export { DocReader } from './DocReader.jsx';
