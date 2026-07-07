// 방언 v1 지식 + 붙여넣기/입력 정규화 — 허용 태그·인라인만 남기고 나머지는 unwrap/제거.
//
// ⚠️ 이 정규화는 UX 편의용이다(붙여넣을 때 즉시 깔끔한 방언으로). 보안 최종
//    방어선은 서버의 parse_dialect (src/juldoc/dialect.py) — 저장 시 재정화한다.
//    두 화이트리스트를 의도적으로 대칭 유지한다 (허용 블록/인라인/스킴 동일).

/** 허용 블록 태그 (h1~h6, p, pre>code, blockquote, ul/ol/li, img, table 계열). */
export const ALLOWED_BLOCKS = new Set([
  'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
  'p', 'pre', 'code', 'blockquote',
  'ul', 'ol', 'li',
  'img', 'table', 'thead', 'tbody', 'tr', 'td', 'th',
]);

/** 허용 인라인 태그 (strong, em, u, a — br 은 줄바꿈 편의로 허용). */
export const ALLOWED_INLINE = new Set(['strong', 'em', 'u', 'a', 'br']);

// 정규화 매핑: b/i 는 허용 태그가 아니라 strong/em 으로 *변환*한다 (왕복 손실 방지).
// execCommand('bold'/'italic') 이 <b>/<i> 를 만드는 브라우저 산출물 대응.
// 서버 src/juldoc/dialect.py 의 _INLINE_ALIASES 와 대칭 유지.
const INLINE_ALIASES = { b: 'strong', i: 'em' };

/** 내용째 버리는 태그 (서버 _DROP_CONTENT 와 동일). */
const DROP_CONTENT = new Set(['script', 'style', 'iframe', 'object', 'embed']);

/** 태그별 허용 속성. 나머지 속성은 전부 제거된다. */
const ALLOWED_ATTRS = {
  a: ['href'],
  img: ['src', 'alt'],
  p: ['style'],
  td: ['colspan', 'rowspan', 'style'],
  th: ['colspan', 'rowspan', 'style'],
  code: ['class'],
};

/** a href / img src 에 허용되는 URL 스킴 (상대경로는 항상 허용). */
const ALLOWED_SCHEMES = new Set(['http:', 'https:']);

/**
 * URL 정화 — 상대경로/http(s) 만 통과, javascript: 등은 빈 문자열.
 * @param {string} url
 * @returns {string}
 */
export function sanitizeUrl(url) {
  const raw = (url || '').trim();
  if (!raw) return '';
  // 스킴이 없으면(상대경로/앵커) 통과.
  if (!/^[a-z][a-z0-9+.-]*:/i.test(raw)) return raw;
  const scheme = raw.slice(0, raw.indexOf(':') + 1).toLowerCase();
  return ALLOWED_SCHEMES.has(scheme) ? raw : '';
}

/** class 값에서 language-* 만 남긴다 (code 하이라이트 힌트). */
function sanitizeCodeClass(value) {
  const langs = (value || '')
    .split(/\s+/)
    .filter((c) => c.startsWith('language-'));
  return langs.join(' ');
}

function copyAllowedAttrs(src, dst, tag) {
  const allowed = ALLOWED_ATTRS[tag];
  if (!allowed) return;
  for (const name of allowed) {
    if (!src.hasAttribute(name)) continue;
    let value = src.getAttribute(name);
    if ((tag === 'a' && name === 'href') || (tag === 'img' && name === 'src')) {
      value = sanitizeUrl(value);
      if (!value) continue;
    } else if (tag === 'code' && name === 'class') {
      value = sanitizeCodeClass(value);
      if (!value) continue;
    }
    dst.setAttribute(name, value);
  }
}

/**
 * 노드 하나를 정화해 target 에 append. 허용 태그는 재생성(속성 화이트리스트),
 * DROP_CONTENT 는 통째로 버림, 그 외 알 수 없는 태그는 unwrap(자식만 승계).
 */
function sanitizeNode(node, target, doc) {
  if (node.nodeType === 3 /* TEXT */) {
    target.appendChild(doc.createTextNode(node.nodeValue));
    return;
  }
  if (node.nodeType !== 1 /* ELEMENT */) return; // 주석 등 무시

  // b→strong, i→em 정규화 매핑을 화이트리스트 검사 전에 적용.
  const rawTag = node.tagName.toLowerCase();
  const tag = INLINE_ALIASES[rawTag] || rawTag;
  if (DROP_CONTENT.has(tag)) return;

  if (ALLOWED_BLOCKS.has(tag) || ALLOWED_INLINE.has(tag)) {
    const el = doc.createElement(tag);
    copyAllowedAttrs(node, el, tag);
    for (const child of Array.from(node.childNodes)) {
      sanitizeNode(child, el, doc);
    }
    target.appendChild(el);
    return;
  }

  // 알 수 없는 블록/인라인 태그: unwrap — 자식만 부모로 승계 (텍스트 보존).
  for (const child of Array.from(node.childNodes)) {
    sanitizeNode(child, target, doc);
  }
}

/**
 * 임의 HTML 조각을 방언으로 정규화한 DocumentFragment 로 반환.
 * 에디터의 paste 핸들러가 삽입 전에 이걸로 정화한다.
 * @param {string} html
 * @param {Document} [doc] 노드를 만들 소유 document (기본 전역 document).
 * @returns {DocumentFragment}
 */
export function normalizeFragment(html, doc = document) {
  const parsed = new DOMParser().parseFromString(html || '', 'text/html');
  const frag = doc.createDocumentFragment();
  for (const child of Array.from(parsed.body.childNodes)) {
    sanitizeNode(child, frag, doc);
  }
  return frag;
}

/**
 * 임의 HTML 조각을 방언으로 정규화한 문자열로 반환.
 * @param {string} html
 * @param {Document} [doc]
 * @returns {string}
 */
export function normalizeHtml(html, doc = document) {
  const holder = doc.createElement('div');
  holder.appendChild(normalizeFragment(html, doc));
  return holder.innerHTML;
}
