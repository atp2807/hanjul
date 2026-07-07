import { screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@hanjul/test-utils';
import * as books from '../services/api/books';
import { StorePage } from './StorePage';

vi.mock('../services/api/books');

function renderStore() {
  return renderWithProviders(<StorePage />);
}

describe('StorePage', () => {
  it('출판된 책 목록을 렌더한다', async () => {
    books.listStore.mockResolvedValue({
      items: [
        { id: '1', title: '한 줄', priceAmt: 12000, coverUrl: null, kind: 'BOOK' },
        { id: '2', title: '웹소설', priceAmt: null, coverUrl: null, kind: 'WEBNOVEL' },
      ],
      count: 2,
    });
    renderStore();
    // 표지 플레이스홀더에도 제목이 들어가 제목은 중복 → 유일한 값으로 단언
    expect(await screen.findByText('12,000원')).toBeInTheDocument();
    expect(screen.getAllByText('한 줄').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('무료')).toBeInTheDocument(); // 웹소설(가격 null)
  });

  it('빈 목록이면 안내 문구', async () => {
    books.listStore.mockResolvedValue({ items: [], count: 0 });
    renderStore();
    expect(await screen.findByText(/아직 출판된 책이 없어요/)).toBeInTheDocument();
  });

  it('카테고리 탭이 보인다', async () => {
    books.listStore.mockResolvedValue({ items: [], count: 0 });
    renderStore();
    expect(await screen.findByText('일반서적')).toBeInTheDocument();
    expect(screen.getByText('웹소설')).toBeInTheDocument();
  });
});
