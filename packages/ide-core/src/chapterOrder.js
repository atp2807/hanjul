// chapterOrder.js — 순수 로직만: 챕터 상태 순환 + id 배열 재배열. DOM/host 의존 없음
// (테스트가 jsdom/네트워크 없이 돌아가게 하기 위한 의도적 분리).

/** 상태점 클릭 순환 순서 — DONE 다음은 다시 DRAFT (dc-2009f043 "●상태점"). */
export const STATUS_CYCLE = ['DRAFT', 'REVISING', 'DONE'];

/**
 * 상태점 클릭 1회 = 다음 상태로 순환. 모르는 값(초기 undefined 등)은 첫 상태(DRAFT)로.
 * @param {string} [status]
 * @returns {string}
 */
export function nextStatus(status) {
  const idx = STATUS_CYCLE.indexOf(status);
  if (idx === -1) return STATUS_CYCLE[0];
  return STATUS_CYCLE[(idx + 1) % STATUS_CYCLE.length];
}

/**
 * HTML5 DnD 드롭 결과 반영 — draggedId 를 targetId 기준 위치로 옮긴 *새* 배열을 반환한다
 * (원본 ids 는 변경하지 않음). draggedId/targetId 가 배열에 없거나 같으면 원본과 동일한
 * (그러나 새로) 배열을 반환해 안전하게 no-op 처리한다.
 * @param {Array<string|number>} ids 현재 순서(챕터 id 배열)
 * @param {string|number} draggedId 드래그된 챕터 id
 * @param {string|number} targetId 드롭 대상 챕터 id
 * @param {{before?: boolean}} [opts] before(기본 true)면 targetId 바로 앞에 삽입, false 면 바로 뒤.
 * @returns {Array<string|number>}
 */
export function moveChapter(ids, draggedId, targetId, { before = true } = {}) {
  if (draggedId === targetId) return ids.slice();
  const from = ids.indexOf(draggedId);
  const to = ids.indexOf(targetId);
  if (from === -1 || to === -1) return ids.slice();

  const next = ids.slice();
  next.splice(from, 1);
  let insertAt = next.indexOf(targetId);
  if (insertAt === -1) return ids.slice(); // 이론상 도달 불가(안전망)
  if (!before) insertAt += 1;
  next.splice(insertAt, 0, draggedId);
  return next;
}
