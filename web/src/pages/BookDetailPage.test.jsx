import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import * as authCtx from '../auth/AuthContext';
import * as booksApi from '../services/api/books';
import * as ordersApi from '../services/api/orders';
import * as reviewsApi from '../services/api/reviews';
import { BookDetailPage } from './BookDetailPage';

const { requestPayment } = vi.hoisted(() => ({ requestPayment: vi.fn() }));
vi.mock('@tosspayments/payment-sdk', () => ({
  loadTossPayments: vi.fn().mockResolvedValue({ requestPayment }),
}));
vi.mock('../auth/AuthContext');
vi.mock('../services/api/books');
vi.mock('../services/api/orders');
vi.mock('../services/api/reviews');
vi.mock('react-router-dom', async (orig) => ({ ...(await orig()), useNavigate: () => vi.fn() }));

const BOOK = { id: 'book-1', title: '테스트책', priceAmt: 5000, authorId: 'a1' };

describe('BookDetailPage 결제', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    authCtx.useAuth.mockReturnValue({ user: { id: 'buyer-1' } });
    booksApi.getStoreDetail.mockResolvedValue(BOOK);
    reviewsApi.getReviews.mockResolvedValue({ average: 0, count: 0, items: [] });
    ordersApi.createOrder.mockResolvedValue({ id: 'order-9', amountAmt: 5000 });
  });

  it('실 결제: 구매 → 토스 결제창(카드) 호출 (orderId·amount·successUrl)', async () => {
    ordersApi.getPaymentConfig.mockResolvedValue({ demo: false, tossClientKey: 'test_ck_abc' });
    render(
      <MemoryRouter>
        <BookDetailPage />
      </MemoryRouter>,
    );
    fireEvent.click(await screen.findByRole('checkbox')); // 청약철회 제한 동의
    fireEvent.click(await screen.findByText('바로 구매'));

    await waitFor(() => expect(requestPayment).toHaveBeenCalled());
    // 서버에 동의 플래그 전달
    expect(ordersApi.createOrder).toHaveBeenCalledWith('book-1', 'SELF', true);
    const [method, opts] = requestPayment.mock.calls[0];
    expect(method).toBe('카드');
    expect(opts.orderId).toBe('order-9');
    expect(opts.amount).toBe(5000);
    expect(opts.orderName).toBe('테스트책');
    expect(opts.successUrl).toContain('/payment/result');
    expect(opts.successUrl).toContain('bookId=book-1');
    expect(ordersApi.confirmPayment).not.toHaveBeenCalled(); // confirm은 결과페이지에서
  });

  it('데모 모드: 결제창 없이 바로 demo confirm', async () => {
    ordersApi.getPaymentConfig.mockResolvedValue({ demo: true, tossClientKey: '' });
    ordersApi.confirmPayment.mockResolvedValue({});
    render(
      <MemoryRouter>
        <BookDetailPage />
      </MemoryRouter>,
    );
    fireEvent.click(await screen.findByRole('checkbox'));
    fireEvent.click(await screen.findByText('바로 구매'));

    await waitFor(() => expect(ordersApi.confirmPayment).toHaveBeenCalledWith('order-9', 'demo'));
    expect(requestPayment).not.toHaveBeenCalled();
  });

  it('청약철회 제한 미동의 시 구매가 차단된다(주문 생성 안 함)', async () => {
    ordersApi.getPaymentConfig.mockResolvedValue({ demo: true, tossClientKey: '' });
    render(
      <MemoryRouter>
        <BookDetailPage />
      </MemoryRouter>,
    );
    // 체크 없이 구매 시도 — 버튼 disabled라 클릭돼도 주문 안 만들어짐
    const buyBtn = await screen.findByText('바로 구매');
    expect(buyBtn).toBeDisabled();
    fireEvent.click(buyBtn);
    await waitFor(() => {}); // flush
    expect(ordersApi.createOrder).not.toHaveBeenCalled();
  });
});

function renderAtBook() {
  return render(
    <MemoryRouter initialEntries={['/books/book-1']}>
      <Routes><Route path="/books/:id" element={<BookDetailPage />} /></Routes>
    </MemoryRouter>,
  );
}

describe('BookDetailPage 리뷰', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    authCtx.useAuth.mockReturnValue({ user: { id: 'buyer-1' } });
    booksApi.getStoreDetail.mockResolvedValue(BOOK);
    ordersApi.getPaymentConfig.mockResolvedValue({ demo: true, tossClientKey: '' });
  });

  it('리뷰 목록 렌더 — 평점·서평단 배지·수정표시', async () => {
    reviewsApi.getReviews.mockResolvedValue({
      average: 4.5,
      count: 2,
      items: [
        { id: 'r1', rating: 5, body: '최고예요', author: '독자1', source: 'REVIEW_COPY', updatedAt: null },
        { id: 'r2', rating: 4, body: '', author: null, source: 'PURCHASE', updatedAt: '2026-07-01T00:00:00Z' },
      ],
    });
    renderAtBook();

    expect(await screen.findByText('최고예요')).toBeInTheDocument();
    expect(screen.getByText('서평단')).toBeInTheDocument();
    expect(screen.getByText('독자1')).toBeInTheDocument();
    expect(screen.getAllByText('익명').length).toBeGreaterThanOrEqual(1); // author 없으면 익명 (Avatar 이니셜에도 등장)
    expect(screen.getByText('(수정됨)')).toBeInTheDocument();
    expect(screen.getByText(/독자 리뷰 · 4.5 \(2\)/)).toBeInTheDocument();
  });

  it('리뷰 없으면 안내 문구', async () => {
    reviewsApi.getReviews.mockResolvedValue({ average: 0, count: 0, items: [] });
    renderAtBook();
    expect(await screen.findByText('아직 리뷰가 없어요.')).toBeInTheDocument();
  });

  it('리뷰 로드 실패 → ErrorNotice + 다시 시도로 복구', async () => {
    reviewsApi.getReviews
      .mockRejectedValueOnce(new Error('API 500'))
      .mockResolvedValueOnce({ average: 0, count: 1, items: [{ id: 'r1', rating: 5, body: '좋아요', author: '독자', source: 'PURCHASE' }] });
    renderAtBook();

    expect(await screen.findByText('리뷰를 불러오지 못했어요.')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '다시 시도' }));
    expect(await screen.findByText('좋아요')).toBeInTheDocument();
  });

  it('리뷰 작성 성공 → 입력값 초기화 + 목록 갱신', async () => {
    reviewsApi.getReviews
      .mockResolvedValueOnce({ average: 0, count: 0, items: [] })
      .mockResolvedValueOnce({ average: 5, count: 1, items: [{ id: 'r1', rating: 5, body: '새 리뷰', author: '나', source: 'PURCHASE' }] });
    reviewsApi.addReview.mockResolvedValue(null);
    renderAtBook();

    await screen.findByText('아직 리뷰가 없어요.');
    fireEvent.change(screen.getByPlaceholderText('리뷰를 남겨주세요 (선택)'), { target: { value: '좋았어요' } });
    fireEvent.click(screen.getByRole('button', { name: '리뷰 등록' }));

    await waitFor(() => expect(reviewsApi.addReview).toHaveBeenCalledWith('book-1', 5, '좋았어요'));
    expect(await screen.findByText('새 리뷰')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('리뷰를 남겨주세요 (선택)')).toHaveValue('');
  });

  it('구매 안 한 독자가 리뷰 시도 → 403 안내', async () => {
    reviewsApi.getReviews.mockResolvedValue({ average: 0, count: 0, items: [] });
    const err = new Error('forbidden'); err.status = 403;
    reviewsApi.addReview.mockRejectedValue(err);
    renderAtBook();

    await screen.findByText('아직 리뷰가 없어요.');
    fireEvent.click(screen.getByRole('button', { name: '리뷰 등록' }));
    expect(await screen.findByText('구매한 독자만 리뷰할 수 있어요.')).toBeInTheDocument();
  });
});
