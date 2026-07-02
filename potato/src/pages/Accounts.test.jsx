import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../api', () => ({
  api: {
    account: vi.fn(),
    suspend: vi.fn(),
    unsuspend: vi.fn(),
    blockReview: vi.fn(),
    unblockReview: vi.fn(),
  },
}));

import { api } from '../api';
import Accounts from './Accounts';

const active = {
  id: 'a1', displayName: '김작가', email: 'k@x.com', roleCd: 'USER',
  statusCd: 'ACTIVE', reviewBlocked: false,
};

function lookup(value = 'a1') {
  fireEvent.change(screen.getByPlaceholderText('00000000-0000-...'), { target: { value } });
  fireEvent.click(screen.getByRole('button', { name: /조회/ }));
}

beforeEach(() => {
  vi.clearAllMocks();
  api.suspend.mockResolvedValue({});
  api.blockReview.mockResolvedValue({});
});

describe('Accounts (운영자 계정관리)', () => {
  it('조회 성공 시 이름·상태를 보여준다', async () => {
    api.account.mockResolvedValue(active);
    render(<Accounts />);
    lookup('a1');
    expect(await screen.findByText('김작가')).toBeInTheDocument();
    expect(screen.getByText('정상')).toBeInTheDocument();
    expect(api.account).toHaveBeenCalledWith('a1');
  });

  it('404면 안내 메시지를 보여준다', async () => {
    api.account.mockRejectedValue({ status: 404 });
    render(<Accounts />);
    lookup('nope');
    expect(await screen.findByText('계정을 찾을 수 없습니다.')).toBeInTheDocument();
  });

  it('정상 계정은 정지 사유 프롬프트 후 suspend를 호출한다', async () => {
    api.account.mockResolvedValue(active);
    vi.spyOn(window, 'prompt').mockReturnValue('약관 위반');
    render(<Accounts />);
    lookup('a1');
    await screen.findByText('김작가');
    fireEvent.click(screen.getByRole('button', { name: '계정 정지' }));
    await waitFor(() => expect(api.suspend).toHaveBeenCalledWith('a1', '약관 위반'));
  });

  it('서평단 자격회수 버튼이 blockReview를 호출한다', async () => {
    api.account.mockResolvedValue(active);
    vi.spyOn(window, 'prompt').mockReturnValue(null);
    render(<Accounts />);
    lookup('a1');
    await screen.findByText('김작가');
    fireEvent.click(screen.getByRole('button', { name: '서평단 자격회수' }));
    await waitFor(() => expect(api.blockReview).toHaveBeenCalledWith('a1', null));
  });
});
