import { fireEvent, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { authFixture, httpError, renderWithProviders } from '@hanjul/test-utils';

const mockNavigate = vi.fn();
const mockLogin = vi.fn();

vi.mock('../api', () => ({
  api: { login: vi.fn() },
}));
vi.mock('../auth.jsx', () => ({
  useOps: () => authFixture({ login: mockLogin }),
}));
vi.mock('react-router-dom', async (orig) => ({
  ...(await orig()),
  useNavigate: () => mockNavigate,
}));

import { api } from '../api';
import Login from './Login';

function fillAndSubmit({ email = 'a@x.com', password = 'pw1234' } = {}) {
  fireEvent.change(screen.getByLabelText('이메일'), { target: { value: email } });
  fireEvent.change(screen.getByLabelText('비밀번호'), { target: { value: password } });
  fireEvent.click(screen.getByRole('button', { name: '로그인' }));
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('Login (운영자 로그인)', () => {
  it('성공 시 login(token) 호출 후 홈으로 이동한다', async () => {
    api.login.mockResolvedValue({ token: 'tok-123' });
    renderWithProviders(<Login />);
    fillAndSubmit();
    await waitFor(() => expect(mockLogin).toHaveBeenCalledWith('tok-123'));
    expect(mockNavigate).toHaveBeenCalledWith('/', { replace: true });
  });

  it('401이면 정확한 안내 메시지를 보여준다', async () => {
    api.login.mockRejectedValue(httpError(401));
    renderWithProviders(<Login />);
    fillAndSubmit();
    expect(await screen.findByText('이메일 또는 비밀번호가 올바르지 않습니다.')).toBeInTheDocument();
    expect(mockLogin).not.toHaveBeenCalled();
  });

  it('401 이외의 실패는 일반 메시지("로그인 실패")를 보여준다', async () => {
    api.login.mockRejectedValue(httpError(500));
    renderWithProviders(<Login />);
    fillAndSubmit();
    expect(await screen.findByText('로그인 실패')).toBeInTheDocument();
  });

  it('제출 중에는 버튼이 비활성화되고 문구가 "확인 중…"으로 바뀐다', async () => {
    let resolveLogin;
    api.login.mockReturnValue(
      new Promise((resolve) => {
        resolveLogin = resolve;
      }),
    );
    renderWithProviders(<Login />);
    fillAndSubmit();
    const busyButton = await screen.findByRole('button', { name: '확인 중…' });
    expect(busyButton).toBeDisabled();
    resolveLogin({ token: 'tok' });
    await waitFor(() => expect(mockLogin).toHaveBeenCalled());
  });

  it('이메일·비밀번호 입력은 필수(required) 필드다', () => {
    renderWithProviders(<Login />);
    expect(screen.getByLabelText('이메일')).toBeRequired();
    expect(screen.getByLabelText('비밀번호')).toBeRequired();
  });
});
