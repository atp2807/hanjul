// 미디어(이미지) src 매핑 — 정본 ↔ 표시 경로 변환.
//
// 규약(스펙): 정본 HTML 에는 이미지가 `/media/{key}` 상대경로로 저장된다(juldoc
// 정본 포맷 보존). 그러나 운영에서 프론트(www.hanjul.io)와 API(api.hanjul.io)
// 오리진이 달라, 실제 표시(리더·에디터)에는 `${apiBase}/api/media/{key}` 절대경로가
// 필요하다. 저장 직렬화 시엔 다시 `/media/{key}` 정본 경로로 되돌린다.
//
// apiBase 계약:
//   - apiBase == null(undefined/null): 매핑하지 않음(passthrough) — 순수 코어 기본.
//   - apiBase === '' (dev, vite proxy): `/media/X` ↔ `/api/media/X` (프록시가 /api 처리).
//   - apiBase === 'https://api.hanjul.io' (prod): `/media/X` ↔ `https://api.hanjul.io/api/media/X`.

const CANON_PREFIX = '/media/';
const API_MEDIA_PREFIX = '/api/media/';

/**
 * 정본 src(`/media/{key}`)를 표시용 절대경로(`${apiBase}/api/media/{key}`)로 매핑.
 * apiBase 가 null/undefined 면 그대로 반환(passthrough). 정본 경로가 아니면 손대지 않음.
 * @param {string} src
 * @param {string|null|undefined} apiBase
 * @returns {string}
 */
export function mediaSrcToDisplay(src, apiBase) {
  if (apiBase == null) return src;
  if (typeof src !== 'string') return src;
  if (src.startsWith(CANON_PREFIX)) return `${apiBase}${API_MEDIA_PREFIX}${src.slice(CANON_PREFIX.length)}`;
  return src;
}

/**
 * 표시용 src(`${apiBase}/api/media/{key}` 또는 `/api/media/{key}`)를 정본(`/media/{key}`)으로 되돌림.
 * apiBase 가 null/undefined 면 그대로 반환(passthrough). 표시 경로가 아니면 손대지 않음.
 * @param {string} src
 * @param {string|null|undefined} apiBase
 * @returns {string}
 */
export function mediaSrcToCanonical(src, apiBase) {
  if (apiBase == null) return src;
  if (typeof src !== 'string') return src;
  // 절대 표시경로(apiBase 접두)를 먼저 벗긴다(비어있지 않을 때만 — 빈 apiBase 는 아래 상대경로 분기).
  const absPrefix = `${apiBase}${API_MEDIA_PREFIX}`;
  if (apiBase && src.startsWith(absPrefix)) return `${CANON_PREFIX}${src.slice(absPrefix.length)}`;
  // 상대 표시경로(/api/media/…) — dev(빈 apiBase) 또는 동일오리진.
  if (src.startsWith(API_MEDIA_PREFIX)) return `${CANON_PREFIX}${src.slice(API_MEDIA_PREFIX.length)}`;
  return src;
}

/**
 * 루트 요소 하위의 모든 <img src> 를 fn 으로 변환(제자리). src 없는 img 는 건너뜀.
 * @param {Element|DocumentFragment} root
 * @param {(src:string)=>string} fn
 */
export function mapImgSrcs(root, fn) {
  for (const img of root.querySelectorAll('img')) {
    const src = img.getAttribute('src');
    if (src != null) img.setAttribute('src', fn(src));
  }
}
