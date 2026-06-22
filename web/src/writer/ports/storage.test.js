import { describe, expect, it } from 'vitest';

import { InMemoryStorage } from './storage';

describe('InMemoryStorage (StoragePort fake)', () => {
  it('save→load 라운드트립', async () => {
    const s = new InMemoryStorage();
    await s.save('bk1', { blocks: [{ type: 'p', spans: [] }] });
    expect(await s.load('bk1')).toEqual({ blocks: [{ type: 'p', spans: [] }] });
  });

  it('없는 id 는 null', async () => {
    expect(await new InMemoryStorage().load('x')).toBeNull();
  });

  it('list 는 최근 저장 순', async () => {
    const s = new InMemoryStorage();
    await s.save('a', {});
    await s.save('b', {});
    await s.save('a', {}); // a 갱신 → 더 최근
    expect(await s.list()).toEqual(['a', 'b']);
  });

  it('remove', async () => {
    const s = new InMemoryStorage();
    await s.save('a', {});
    await s.remove('a');
    expect(await s.load('a')).toBeNull();
  });
});
