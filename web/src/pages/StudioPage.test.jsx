import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import * as authorsApi from '../services/api/authors';
import * as studioApi from '../services/api/studio';
import { StudioPage } from './StudioPage';

vi.mock('../services/api/studio', async (o) => ({
  ...(await o()),
  getMyBooks: vi.fn(),
  getSales: vi.fn(),
  createBook: vi.fn(),
}));
vi.mock('../services/api/authors', async (o) => ({ ...(await o()), updateProfile: vi.fn() }));

let mockAuth = { user: { id: 'u1', displayName: '박작가', bio: '' }, loading: false };
vi.mock('../auth/AuthContext', () => ({ useAuth: () => mockAuth }));

const navigate = vi.fn();
vi.mock('react-router-dom', async (orig) => ({ ...(await orig()), useNavigate: () => navigate }));

function renderPage() {
  return render(<MemoryRouter><StudioPage /></MemoryRouter>);
}

const SALES = { totalPayout: 67690, totalOrders: 12, totalRevenue: 120000, books: [{ bookId: 'b1', orderCount: 12, payout: 67690 }] };
const BOOKS = { items: [{ id: 'b1', title: '밤의 편집자', status: 'PUBLISHED' }] };

describe('StudioPage', () => {
  beforeEach(() => {
    navigate.mockClear();
    studioApi.createBook.mockClear();
    mockAuth = { user: { id: 'u1', displayName: '박작가', bio: '' }, loading: false };
  });

  it('로그인 안 됐으면 안내만', () => {
    mockAuth = { user: null, loading: false };
    renderPage();
    expect(screen.getByText('로그인이 필요해요.')).toBeInTheDocument();
  });

  it('auth 로딩 중이면 대기 문구', () => {
    mockAuth = { user: null, loading: true };
    renderPage();
    expect(screen.getByText('불러오는 중…')).toBeInTheDocument();
  });

  it('책 목록 + 매출 집계 렌더', async () => {
    studioApi.getMyBooks.mockResolvedValue(BOOKS);
    studioApi.getSales.mockResolvedValue(SALES);
    renderPage();

    expect(await screen.findByText('밤의 편집자')).toBeInTheDocument();
    expect(screen.getAllByText('67,690원').length).toBeGreaterThanOrEqual(1); // 상단 집계 + 책별 수익
    expect(screen.getAllByText('12권').length).toBeGreaterThanOrEqual(1); // 상단 집계 + 책별 판매
    expect(screen.getByText('판매중')).toBeInTheDocument();
  });

  it('책이 없으면 빈 상태 안내', async () => {
    studioApi.getMyBooks.mockResolvedValue({ items: [] });
    studioApi.getSales.mockResolvedValue({ ...SALES, books: [] });
    renderPage();
    expect(await screen.findByText(/아직 쓴 책이 없어요/)).toBeInTheDocument();
  });

  it('새 책 만들기 → 생성 후 편집 페이지로 이동', async () => {
    studioApi.getMyBooks.mockResolvedValue({ items: [] });
    studioApi.getSales.mockResolvedValue({ ...SALES, books: [] });
    studioApi.createBook.mockResolvedValue({ bookId: 'new1' });
    renderPage();
    await screen.findByText(/아직 쓴 책이 없어요/);

    fireEvent.change(screen.getByPlaceholderText('새 책 제목'), { target: { value: '신작' } });
    fireEvent.click(screen.getByRole('button', { name: '새 책 만들기' }));
    await waitFor(() => expect(studioApi.createBook).toHaveBeenCalledWith('신작'));
    expect(navigate).toHaveBeenCalledWith('/studio/new1');
  });

  it('제목 없이 제출하면 생성 API 호출 안 함', async () => {
    studioApi.getMyBooks.mockResolvedValue({ items: [] });
    studioApi.getSales.mockResolvedValue({ ...SALES, books: [] });
    renderPage();
    await screen.findByText(/아직 쓴 책이 없어요/);
    fireEvent.click(screen.getByRole('button', { name: '새 책 만들기' }));
    expect(studioApi.createBook).not.toHaveBeenCalled();
  });

  it('작가 소개 저장 성공 → 확인 메시지', async () => {
    studioApi.getMyBooks.mockResolvedValue({ items: [] });
    studioApi.getSales.mockResolvedValue({ ...SALES, books: [] });
    authorsApi.updateProfile.mockResolvedValue(null);
    renderPage();
    await screen.findByText(/아직 쓴 책이 없어요/);

    fireEvent.change(screen.getByTestId('bio-input'), { target: { value: '새 소개' } });
    fireEvent.click(screen.getByRole('button', { name: '소개 저장' }));
    expect(await screen.findByText('작가 소개를 저장했어요.')).toBeInTheDocument();
    expect(authorsApi.updateProfile).toHaveBeenCalledWith('새 소개');
  });

  it('작가 소개 저장 실패 → 실패 메시지 (침묵 금지)', async () => {
    studioApi.getMyBooks.mockResolvedValue({ items: [] });
    studioApi.getSales.mockResolvedValue({ ...SALES, books: [] });
    authorsApi.updateProfile.mockRejectedValue(new Error('네트워크 오류'));
    renderPage();
    await screen.findByText(/아직 쓴 책이 없어요/);

    fireEvent.click(screen.getByRole('button', { name: '소개 저장' }));
    expect(await screen.findByText(/저장 실패: 네트워크 오류/)).toBeInTheDocument();
  });
});
