// 되돌리기 지점(스냅샷) — 버전 blob 을 Y.Array 에 저장. 복원 = 에디터 내용 교체.
// Yjs Array 라 로컬 영속(y-indexeddb) + 동기화(y-websocket)에 자동으로 따라온다.
// 각 항목: { id, ts, neutral } (neutral = 그 시점 중립 doc, immutable blob).

const KEY = 'snapshots';
const MAX = 30; // 오래된 지점 자동 정리 (Y.Doc 무한 증가 방지)

export function takeSnapshot(ydoc, neutral, ts) {
  const arr = ydoc.getArray(KEY);
  // id 에 clientID 포함 → 다기기 동시 push 시에도 충돌 없음(React key)
  arr.push([{ id: `${ts}-${ydoc.clientID}-${arr.length}`, ts, neutral }]);
  if (arr.length > MAX) arr.delete(0, arr.length - MAX);
}

// 최신순
export function listSnapshots(ydoc) {
  return ydoc.getArray(KEY).toArray().slice().reverse();
}

export function observeSnapshots(ydoc, cb) {
  const arr = ydoc.getArray(KEY);
  const handler = () => cb(listSnapshots(ydoc));
  arr.observe(handler);
  return () => arr.unobserve(handler);
}
