import { screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders, authFixture } from '@hanjul/test-utils';
import { AuthCallbackPage } from './AuthCallbackPage';

const login = vi.fn();
vi.mock('../auth/AuthContext', () => ({ useAuth: () => authFixture({ login }) }));

const navigate = vi.fn();
vi.mock('react-router-dom', async (orig) => ({ ...(await orig()), useNavigate: () => navigate }));

function renderAt(hash) {
  window.location.hash = hash;
  return renderWithProviders(<AuthCallbackPage />, { path: '/auth/callback', at: `/auth/callback${hash}` });
}

describe('AuthCallbackPage', () => {
  beforeEach(() => { login.mockClear(); navigate.mockClear(); });

  it('token 있으면 로그인 처리 후 홈으로', () => {
    renderAt('#token=abc123&isNew=0');
    expect(login).toHaveBeenCalledWith('abc123');
    expect(navigate).toHaveBeenCalledWith('/', { replace: true });
  });

  it('알려진 error 코드 → 안내 문구', () => {
    renderAt('#error=access_denied');
    expect(screen.getByText('로그인을 취소했어요.')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '홈으로' })).toBeInTheDocument();
  });

  it('모르는 error 코드 → 일반 문구 (침묵 금지)', () => {
    renderAt('#error=weird_unknown_code');
    expect(screen.getByText('로그인에 실패했어요.')).toBeInTheDocument();
  });

  it('token도 error도 없으면 홈으로 리다이렉트', () => {
    renderAt('');
    expect(navigate).toHaveBeenCalledWith('/', { replace: true });
    expect(login).not.toHaveBeenCalled();
  });
});
