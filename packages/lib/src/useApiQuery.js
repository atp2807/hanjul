// 공용 조회 훅 — 로딩/에러/재시도를 한 곳으로 (침묵 .catch(() => setX([])) 패턴 대체).
import { useCallback, useEffect, useState } from 'react';

/**
 * API 조회 상태 관리. fetcher 실패가 조용히 빈 목록으로 둔갑하지 않게 error 를 노출한다.
 * @param {() => Promise<any>} fetcher 호출할 API 함수 (deps 바뀔 때마다 재실행)
 * @param {any[]} [deps=[]] 재조회 의존성 (useEffect deps 와 동일 규칙)
 * @param {{ enabled?: boolean }} [opts] enabled=false 면 조회 보류 (예: 로그인 전)
 * @returns {{ data: any, loading: boolean, error: Error|null, reload: () => void }}
 */
export function useApiQuery(fetcher, deps = [], { enabled = true } = {}) {
  // loading 은 항상 true 로 시작 — enabled 가 나중에 켜져도(로그인 확인 후 등)
  // "loading=false && data=null" 인 프레임이 없도록 (data.items 접근 크래시 방지).
  const [state, setState] = useState({ data: null, loading: true, error: null });
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (!enabled) return undefined; // 보류 중엔 loading 유지
    let alive = true; // 언마운트/재조회 후 늦게 도착한 응답 무시
    setState((s) => ({ ...s, loading: true, error: null }));
    fetcher()
      .then((data) => alive && setState({ data, loading: false, error: null }))
      .catch((error) => alive && setState({ data: null, loading: false, error }));
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick, enabled]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { ...state, reload };
}
