import { act, renderHook, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { useApiQuery } from '@hanjul/lib';

describe('useApiQuery', () => {
  it('성공 — data 채우고 loading 해제', async () => {
    const { result } = renderHook(() => useApiQuery(() => Promise.resolve({ items: [1] })));
    expect(result.current.loading).toBe(true);
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data).toEqual({ items: [1] });
    expect(result.current.error).toBeNull();
  });

  it('실패 — error 노출 (침묵 금지), reload 로 재시도', async () => {
    const fetcher = vi.fn()
      .mockRejectedValueOnce(new Error('boom'))
      .mockResolvedValueOnce({ ok: true });
    const { result } = renderHook(() => useApiQuery(fetcher));
    await waitFor(() => expect(result.current.error).toBeTruthy());
    expect(result.current.data).toBeNull();

    act(() => result.current.reload());
    await waitFor(() => expect(result.current.data).toEqual({ ok: true }));
    expect(result.current.error).toBeNull();
  });

  it('enabled=false — 조회 보류 (로그인 전)', async () => {
    const fetcher = vi.fn().mockResolvedValue({});
    renderHook(() => useApiQuery(fetcher, [], { enabled: false }));
    await new Promise((r) => setTimeout(r, 10));
    expect(fetcher).not.toHaveBeenCalled();
  });

  it('deps 변경 — 재조회', async () => {
    const fetcher = vi.fn((id) => Promise.resolve(id));
    const { result, rerender } = renderHook(({ id }) => useApiQuery(() => fetcher(id), [id]), {
      initialProps: { id: 'a' },
    });
    await waitFor(() => expect(result.current.data).toBe('a'));
    rerender({ id: 'b' });
    await waitFor(() => expect(result.current.data).toBe('b'));
  });
});
