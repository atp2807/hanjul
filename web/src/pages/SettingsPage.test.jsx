import { fireEvent, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders, authFixture } from '@hanjul/test-utils';
import * as auth from '../services/api/auth';
import { SettingsPage } from './SettingsPage';

const mockLogout = vi.fn();
const mockNavigate = vi.fn();
let mockUser = { displayName: '나', email: 'me@x.com' };

vi.mock('../services/api/auth');
vi.mock('../auth/AuthContext', () => ({
  useAuth: () => authFixture({ user: mockUser, logout: mockLogout }),
}));
vi.mock('react-router-dom', async (orig) => ({
  ...(await orig()),
  useNavigate: () => mockNavigate,
}));

function renderSettings() {
  return renderWithProviders(<SettingsPage />);
}

describe('SettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUser = { displayName: '나', email: 'me@x.com' };
  });

  it('내 계정 정보를 보여준다', () => {
    renderSettings();
    expect(screen.getByText(/me@x.com/)).toBeInTheDocument();
  });

  it('비로그인 시 로그인 안내', () => {
    mockUser = null;
    renderSettings();
    expect(screen.getByText(/로그인이 필요해요/)).toBeInTheDocument();
  });

  it('탈퇴는 2단계 확인 후에만 API를 호출한다', async () => {
    auth.withdraw.mockResolvedValue(null);
    renderSettings();

    // 1단계: '회원 탈퇴' 클릭 — 아직 API 호출 안 함
    fireEvent.click(screen.getByRole('button', { name: '회원 탈퇴' }));
    expect(auth.withdraw).not.toHaveBeenCalled();
    expect(screen.getByText(/정말 탈퇴하시겠어요/)).toBeInTheDocument();

    // 2단계: 확정 → API 호출 + 로그아웃 + 홈 이동
    fireEvent.click(screen.getByRole('button', { name: /네, 탈퇴할게요/ }));
    await waitFor(() => expect(auth.withdraw).toHaveBeenCalledTimes(1));
    expect(mockLogout).toHaveBeenCalled();
    expect(mockNavigate).toHaveBeenCalledWith('/', { replace: true });
  });

  it('탈퇴 확인을 취소하면 API 미호출', () => {
    renderSettings();
    fireEvent.click(screen.getByRole('button', { name: '회원 탈퇴' }));
    fireEvent.click(screen.getByRole('button', { name: '취소' }));
    expect(screen.queryByText(/정말 탈퇴하시겠어요/)).not.toBeInTheDocument();
    expect(auth.withdraw).not.toHaveBeenCalled();
  });

  it('내 정보 내려받기가 export API를 호출한다', async () => {
    auth.exportMyData.mockResolvedValue({ account: { email: 'me@x.com' } });
    // jsdom 다운로드 부작용 무력화
    vi.stubGlobal('URL', { createObjectURL: () => 'blob:x', revokeObjectURL: () => {} });
    renderSettings();
    fireEvent.click(screen.getByRole('button', { name: '내 정보 내려받기' }));
    await waitFor(() => expect(auth.exportMyData).toHaveBeenCalledTimes(1));
  });

  it('바로가기 — 서재·정산·알림·스튜디오로 가는 실제 링크가 있다', () => {
    renderSettings();
    expect(screen.getByRole('link', { name: /내 서재/ })).toHaveAttribute('href', '/library');
    expect(screen.getByRole('link', { name: /정산·출금/ })).toHaveAttribute('href', '/settlement');
    expect(screen.getByRole('link', { name: /알림/ })).toHaveAttribute('href', '/notifications');
    expect(screen.getByRole('link', { name: /작가 스튜디오/ })).toHaveAttribute('href', '/studio');
  });
});
