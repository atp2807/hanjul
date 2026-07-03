import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import * as auth from '../services/api/auth';
import { LoginPage } from './LoginPage';

vi.mock('../services/api/auth', async (o) => ({ ...(await o()), getLoginUrl: vi.fn() }));

describe('LoginPage', () => {
  it('Google 버튼 클릭 → authorizationUrl 로 이동', async () => {
    auth.getLoginUrl.mockResolvedValue({ authorizationUrl: 'https://accounts.google.com/x' });
    delete window.location;
    window.location = { href: '' };
    render(<LoginPage />);

    fireEvent.click(screen.getByRole('button', { name: 'Google로 계속하기' }));
    expect(screen.getByRole('button')).toHaveTextContent('이동 중…');
    await waitFor(() => expect(window.location.href).toBe('https://accounts.google.com/x'));
    expect(auth.getLoginUrl).toHaveBeenCalledWith('google');
  });

  it('로그인 URL 조회 실패 → 버튼 다시 활성화 (무한 로딩 방지)', async () => {
    auth.getLoginUrl.mockRejectedValue(new Error('network'));
    render(<LoginPage />);

    const btn = screen.getByRole('button', { name: 'Google로 계속하기' });
    fireEvent.click(btn);
    await waitFor(() => expect(btn).not.toBeDisabled());
    expect(btn).toHaveTextContent('Google로 계속하기');
  });
});
