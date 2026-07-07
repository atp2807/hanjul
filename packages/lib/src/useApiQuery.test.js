// useApiQuery() — 공용 조회 훅 실코드 테스트.
// web/src/hooks/useApiQuery.test.jsx 가 동일 훅(재수출)을 이미 일부 커버하지만,
// 여기(정본 소스)에서 직접 검증하고 stale-response 경합 방지(alive 가드)까지 추가로 확인한다.
import { act, renderHook, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { useApiQuery } from './useApiQuery.js';

describe('useApiQuery', () => {
  it('초기 상태 — loading true, data/error null', () => {
    const fetcher = vi.fn(() => new Promise(() => {})); // 영원히 미해결
    const { result } = renderHook(() => useApiQuery(fetcher));
    expect(result.current.loading).toBe(true);
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it('enabled=false — fetcher를 호출하지 않고 loading을 유지한다', async () => {
    const fetcher = vi.fn().mockResolvedValue({ ok: true });
    const { result } = renderHook(() => useApiQuery(fetcher, [], { enabled: false }));
    await new Promise((r) => setTimeout(r, 10));
    expect(fetcher).not.toHaveBeenCalled();
    expect(result.current.loading).toBe(true);
  });

  it('성공 — data 반영, loading 해제, error null', async () => {
    const fetcher = vi.fn().mockResolvedValue({ items: [1, 2] });
    const { result } = renderHook(() => useApiQuery(fetcher));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data).toEqual({ items: [1, 2] });
    expect(result.current.error).toBeNull();
  });

  it('실패 — error를 침묵 없이 노출한다 (빈 배열로 둔갑 금지)', async () => {
    const err = new Error('서버 에러');
    const fetcher = vi.fn().mockRejectedValue(err);
    const { result } = renderHook(() => useApiQuery(fetcher));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBe(err);
    expect(result.current.data).toBeNull();
  });

  it('reload() — 실패 후 재시도하면 다시 fetcher를 호출해 데이터를 갱신한다', async () => {
    const fetcher = vi.fn()
      .mockRejectedValueOnce(new Error('일시 오류'))
      .mockResolvedValueOnce({ ok: true });
    const { result } = renderHook(() => useApiQuery(fetcher));
    await waitFor(() => expect(result.current.error).toBeTruthy());

    act(() => result.current.reload());

    await waitFor(() => expect(result.current.data).toEqual({ ok: true }));
    expect(result.current.error).toBeNull();
    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  it('deps 변경 — 재조회되어 최신 값을 반영한다', async () => {
    const fetcher = vi.fn((id) => Promise.resolve(`data-${id}`));
    const { result, rerender } = renderHook(
      ({ id }) => useApiQuery(() => fetcher(id), [id]),
      { initialProps: { id: 'a' } },
    );
    await waitFor(() => expect(result.current.data).toBe('data-a'));

    rerender({ id: 'b' });

    await waitFor(() => expect(result.current.data).toBe('data-b'));
    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  it('deps 변경 전 요청의 응답이 늦게 도착해도 무시한다 (stale response 경합 방지)', async () => {
    let resolveFirst;
    const first = new Promise((res) => { resolveFirst = res; });
    const fetcher = vi.fn()
      .mockImplementationOnce(() => first)
      .mockImplementationOnce(() => Promise.resolve('second'));
    const { result, rerender } = renderHook(
      ({ id }) => useApiQuery(() => fetcher(id), [id]),
      { initialProps: { id: 'a' } },
    );

    rerender({ id: 'b' });
    await waitFor(() => expect(result.current.data).toBe('second'));

    resolveFirst('first-stale');
    await new Promise((r) => setTimeout(r, 10));

    expect(result.current.data).toBe('second'); // 첫 요청의 뒤늦은 응답이 덮어쓰지 않아야 함
  });

  it('언마운트 후 응답이 도착해도 에러 없이 무시한다', async () => {
    let resolve;
    const fetcher = vi.fn(() => new Promise((res) => { resolve = res; }));
    const { unmount } = renderHook(() => useApiQuery(fetcher));

    unmount();

    expect(() => resolve({ ok: true })).not.toThrow();
    await new Promise((r) => setTimeout(r, 10));
  });
});
