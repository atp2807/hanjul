import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { MobileTabBar } from './MobileTabBar';

vi.mock('../auth/AuthContext', () => ({ useAuth: () => ({ user: null }) }));

function setMatch(matches) {
  window.matchMedia = vi.fn().mockImplementation((query) => ({
    matches, media: query, addEventListener: vi.fn(), removeEventListener: vi.fn(),
  }));
}

afterEach(() => { delete window.matchMedia; });

describe('MobileTabBar', () => {
  it('모바일 폭에선 5개 탭을 렌더한다', () => {
    setMatch(true);
    render(<MemoryRouter><MobileTabBar /></MemoryRouter>);
    ['홈', '서평단', '서재', '스튜디오', '마이'].forEach((t) => expect(screen.getByText(t)).toBeInTheDocument());
  });

  it('데스크톱 폭에선 렌더하지 않는다', () => {
    setMatch(false);
    const { container } = render(<MemoryRouter><MobileTabBar /></MemoryRouter>);
    expect(container).toBeEmptyDOMElement();
  });

  it('몰입 화면(리더)에선 숨긴다', () => {
    setMatch(true);
    const { container } = render(
      <MemoryRouter initialEntries={['/read/abc']}><MobileTabBar /></MemoryRouter>,
    );
    expect(container).toBeEmptyDOMElement();
  });
});
