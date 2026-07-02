import { render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ErrorBoundary } from '@hanjul/lib';

function Boom() {
  throw new Error('터졌다');
}

describe('ErrorBoundary', () => {
  beforeEach(() => {
    // 경계가 잡는 에러의 console.error 노이즈 억제
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('정상 자식은 그대로 렌더한다', () => {
    render(<ErrorBoundary><div>본문</div></ErrorBoundary>);
    expect(screen.getByText('본문')).toBeInTheDocument();
  });

  it('자식이 던진 예외를 잡아 폴백 UI를 보여준다', () => {
    render(<ErrorBoundary><Boom /></ErrorBoundary>);
    expect(screen.getByText('문제가 발생했어요')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '새로고침' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '홈으로' })).toBeInTheDocument();
  });
});
