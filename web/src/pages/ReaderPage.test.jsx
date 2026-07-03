import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import * as booksApi from '../services/api/books';
import * as ordersApi from '../services/api/orders';
import { ReaderPage } from './ReaderPage';

vi.mock('../services/api/books', async (o) => ({ ...(await o()), getBookContent: vi.fn() }));
vi.mock('../services/api/orders', async (o) => ({ ...(await o()), createOrder: vi.fn(), confirmPayment: vi.fn() }));
vi.mock('../reader/Reader', () => ({ Reader: ({ blocks }) => <div data-testid="reader-view">{blocks.length}블록</div> }));

let mockUser = { id: 'u1' };
vi.mock('../auth/AuthContext', () => ({ useAuth: () => ({ user: mockUser }) }));

const CONTENT = {
  isPreview: false,
  priceAmt: 9900,
  chapters: [{ blocks: [{ id: 'b1', blockType: 'p', html: '<p>본문</p>' }] }],
};

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/read/book1']}>
      <Routes><Route path="/read/:id" element={<ReaderPage />} /></Routes>
    </MemoryRouter>,
  );
}

describe('ReaderPage', () => {
  beforeEach(() => { localStorage.clear(); mockUser = { id: 'u1' }; });

  it('본문 로드 → Reader 렌더', async () => {
    booksApi.getBookContent.mockResolvedValue(CONTENT);
    renderPage();
    expect(await screen.findByTestId('reader-view')).toHaveTextContent('1블록');
  });

  it('로드 실패 → 에러 메시지 표시', async () => {
    booksApi.getBookContent.mockRejectedValue(new Error('네트워크 오류'));
    renderPage();
    expect(await screen.findByText('네트워크 오류')).toBeInTheDocument();
  });

  it('미리보기(isPreview) → 구매 CTA + 가격 표시', async () => {
    booksApi.getBookContent.mockResolvedValue({ ...CONTENT, isPreview: true });
    renderPage();
    expect(await screen.findByText(/9,900원/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '구매하고 계속 읽기' })).toBeInTheDocument();
  });

  it('미로그인 상태 미리보기 → 로그인 유도 문구', async () => {
    mockUser = null;
    booksApi.getBookContent.mockResolvedValue({ ...CONTENT, isPreview: true });
    renderPage();
    expect(await screen.findByRole('button', { name: '로그인하고 구매' })).toBeInTheDocument();
  });

  it('구매 성공 → 재로드로 전체 본문 반영', async () => {
    booksApi.getBookContent
      .mockResolvedValueOnce({ ...CONTENT, isPreview: true })
      .mockResolvedValueOnce({ ...CONTENT, isPreview: false });
    ordersApi.createOrder.mockResolvedValue({ id: 'o1' });
    ordersApi.confirmPayment.mockResolvedValue(null);
    renderPage();

    fireEvent.click(await screen.findByRole('button', { name: '구매하고 계속 읽기' }));
    await waitFor(() => expect(ordersApi.confirmPayment).toHaveBeenCalledWith('o1', 'demo'));
    await waitFor(() => expect(screen.queryByRole('button', { name: /구매/ })).not.toBeInTheDocument());
  });

  it('이미 소유(409) → 조용히 재로드로 회복 (에러 아님)', async () => {
    booksApi.getBookContent
      .mockResolvedValueOnce({ ...CONTENT, isPreview: true })
      .mockResolvedValueOnce({ ...CONTENT, isPreview: false });
    const err = new Error('conflict'); err.status = 409;
    ordersApi.createOrder.mockRejectedValue(err);
    renderPage();

    fireEvent.click(await screen.findByRole('button', { name: '구매하고 계속 읽기' }));
    await waitFor(() => expect(screen.queryByRole('button', { name: /구매/ })).not.toBeInTheDocument());
    expect(screen.queryByText(/구매 실패/)).not.toBeInTheDocument();
  });

  it('구매 실패(그 외) → 에러 안내', async () => {
    booksApi.getBookContent.mockResolvedValue({ ...CONTENT, isPreview: true });
    ordersApi.createOrder.mockRejectedValue(new Error('결제 서버 오류'));
    renderPage();

    fireEvent.click(await screen.findByRole('button', { name: '구매하고 계속 읽기' }));
    expect(await screen.findByText(/구매 실패: 결제 서버 오류/)).toBeInTheDocument();
  });

  it('독서 메모 — 입력 시 로컬스토리지에 책별로 저장', async () => {
    booksApi.getBookContent.mockResolvedValue(CONTENT);
    renderPage();
    const memo = await screen.findByTestId('reader-memo');
    fireEvent.change(memo, { target: { value: '좋은 구절' } });
    expect(localStorage.getItem('hanjul-reader-memo-book1')).toBe('좋은 구절');
  });
});
