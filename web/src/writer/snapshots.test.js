import * as Y from 'yjs';
import { describe, expect, it } from 'vitest';

import { listSnapshots, observeSnapshots, takeSnapshot } from './snapshots';

const neutral = (t) => ({ blocks: [{ type: 'p', spans: [{ text: t, marks: [] }] }] });

describe('snapshots', () => {
  it('저장 → 최신순 목록', () => {
    const doc = new Y.Doc();
    takeSnapshot(doc, neutral('A'), 1000);
    takeSnapshot(doc, neutral('B'), 2000);
    const list = listSnapshots(doc);
    expect(list.map((s) => s.ts)).toEqual([2000, 1000]); // 최신 먼저
    expect(list[1].neutral.blocks[0].spans[0].text).toBe('A'); // blob 보존
  });

  it('MAX 초과 시 오래된 지점 자동 정리', () => {
    const doc = new Y.Doc();
    for (let i = 0; i < 35; i++) takeSnapshot(doc, neutral('v' + i), 1000 + i);
    const list = listSnapshots(doc);
    expect(list.length).toBe(30); // 상한 유지
    expect(list[0].ts).toBe(1034); // 최신 보존
    expect(list.some((s) => s.ts === 1000)).toBe(false); // 가장 오래된 것 제거
  });

  it('observe 가 변경 시 콜백', () => {
    const doc = new Y.Doc();
    let latest = null;
    const off = observeSnapshots(doc, (l) => (latest = l));
    takeSnapshot(doc, neutral('X'), 1000);
    expect(latest.length).toBe(1);
    off();
    takeSnapshot(doc, neutral('Y'), 2000);
    expect(latest.length).toBe(1); // 해제 후 더 안 옴
  });
});
