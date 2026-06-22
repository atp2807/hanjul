// StoragePort — 로컬 영속 계약 (안 날아감의 핵심). 어댑터 교체점.
//   web      → IndexedDBStorage (y-indexeddb 기반, 다음 증분)
//   desktop  → FsStorage (실제 .md/.txt 파일, Phase 1)
//   test     → InMemoryStorage (아래)
//
// 계약: save/load/list/remove. 타이핑 핫패스에서 호출되므로 구현은 비동기·논블로킹.
//
// /**
//  * @typedef {Object} StoragePort
//  * @property {(id: string, doc: object) => Promise<void>} save
//  * @property {(id: string) => Promise<object|null>} load
//  * @property {() => Promise<string[]>} list
//  * @property {(id: string) => Promise<void>} remove
//  */

export class InMemoryStorage {
  constructor() {
    this._map = new Map();
    this._seq = 0; // 결정적 updatedAt (테스트용, Date 비의존)
  }

  async save(id, doc) {
    this._map.set(id, { id, doc, updatedAt: ++this._seq });
  }

  async load(id) {
    return this._map.get(id)?.doc ?? null;
  }

  async list() {
    return [...this._map.values()].sort((a, b) => b.updatedAt - a.updatedAt).map((r) => r.id);
  }

  async remove(id) {
    this._map.delete(id);
  }
}
