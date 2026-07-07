// ErrorBoundary — 렌더 에러 경계 실코드 테스트.
// web/src/components/ErrorBoundary.test.jsx 가 기본 렌더/폴백만 커버하므로,
// 여기(정본 소스)에서는 그에 더해 title/home prop, 재시도·홈 버튼의 실제 동작까지 검증한다.
import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ErrorBoundary } from './ErrorBoundary.jsx';

function Boom() {
  throw new Error('터졌다');
}

describe('ErrorBoundary', () => {
  beforeEach(() => {
    // 경계가 잡는 에러의 console.error 노이즈 억제 (componentDidCatch 로깅)
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('정상 자식은 그대로 렌더한다 (폴백 UI 없음)', () => {
    render(<ErrorBoundary><div>본문</div></ErrorBoundary>);
    expect(screen.getByText('본문')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '새로고침' })).not.toBeInTheDocument();
  });

  it('자식이 던진 예외를 잡아 기본 제목의 폴백 UI를 보여준다', () => {
    render(<ErrorBoundary><Boom /></ErrorBoundary>);
    expect(screen.getByText('문제가 발생했어요')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '새로고침' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '홈으로' })).toBeInTheDocument();
  });

  it('title prop을 지정하면 기본 문구 대신 그 제목을 보여준다', () => {
    render(<ErrorBoundary title="스튜디오 오류"><Boom /></ErrorBoundary>);
    expect(screen.getByText('스튜디오 오류')).toBeInTheDocument();
    expect(screen.queryByText('문제가 발생했어요')).not.toBeInTheDocument();
  });

  it("'새로고침' 버튼 — window.location.reload()를 호출한다", () => {
    const reload = vi.fn();
    const originalLocation = window.location;
    delete window.location;
    window.location = { ...originalLocation, reload };

    render(<ErrorBoundary><Boom /></ErrorBoundary>);
    fireEvent.click(screen.getByRole('button', { name: '새로고침' }));

    expect(reload).toHaveBeenCalledTimes(1);
    window.location = originalLocation;
  });

  it("'홈으로' 버튼 — 기본은 '/', home prop을 주면 그 경로로 이동한다", () => {
    const originalLocation = window.location;
    delete window.location;
    window.location = { ...originalLocation, href: '' };

    render(<ErrorBoundary home="/studio"><Boom /></ErrorBoundary>);
    fireEvent.click(screen.getByRole('button', { name: '홈으로' }));

    expect(window.location.href).toBe('/studio');
    window.location = originalLocation;
  });
});
