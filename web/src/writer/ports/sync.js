// SyncPort — 서버 백그라운드 동기화 계약 (보이지 않는 업로드). 어댑터 교체점.
//   web/desktop → WebSocketSync (y-websocket, 다음 증분)
//   오프라인/test → NullSync (아래)
//
// 계약: push(로컬→서버), pull(서버→로컬), status('synced'|'offline'|'syncing').
// CRDT 기반이라 push/pull 은 멱등·충돌 없음.

export class NullSync {
  async push() {
    /* no-op — 로컬에만 머무름 */
  }

  async pull() {
    return null;
  }

  get status() {
    return 'offline';
  }
}
