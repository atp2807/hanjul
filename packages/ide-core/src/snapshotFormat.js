// snapshotFormat.js — 스냅샷 패널(app.js)이 쓰는 순수 포맷 함수. DOM 의존이 없어
// vitest(environment: 'node')로 그대로 검증할 수 있다(chapterOrder.js 와 같은 이유로 분리).

/**
 * store.py 가 돌려주는 createdAt("YYYY-MM-DDTHH:MM:SS")을 패널 표시용으로 다듬는다 —
 * 초 단위는 스냅샷 목록에서 불필요한 정밀도라 생략.
 * @param {string|null|undefined} createdAt
 * @returns {string}
 */
export function formatSnapshotTimestamp(createdAt) {
  if (!createdAt) return '';
  const [datePart, timePart = ''] = createdAt.split('T');
  return `${datePart} ${timePart.slice(0, 5)}`.trim();
}

/**
 * 자동 스냅샷은 label 이 null(HOST_PORT.md 계약) — 패널에는 "자동 저장"으로 표시한다.
 * @param {string|null|undefined} label
 * @returns {string}
 */
export function formatSnapshotLabel(label) {
  return label || '자동 저장';
}
