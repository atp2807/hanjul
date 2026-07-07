import { screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders, authFixture } from '@hanjul/test-utils';
import { MobileTabBar } from './MobileTabBar';

vi.mock('../auth/AuthContext', () => ({ useAuth: () => authFixture({ user: null }) }));

function setMatch(matches) {
  window.matchMedia = vi.fn().mockImplementation((query) => ({
    matches, media: query, addEventListener: vi.fn(), removeEventListener: vi.fn(),
  }));
}

afterEach(() => { delete window.matchMedia; });

describe('MobileTabBar', () => {
  it('모바일 폭에선 5개 탭을 렌더한다', () => {
    setMatch(true);
    renderWithProviders(<MobileTabBar />);
    ['홈', '서평단', '서재', '스튜디오', '마이'].forEach((t) => expect(screen.getByText(t)).toBeInTheDocument());
  });

  it('데스크톱 폭에선 렌더하지 않는다', () => {
    setMatch(false);
    const { container } = renderWithProviders(<MobileTabBar />);
    expect(container).toBeEmptyDOMElement();
  });

  it('몰입 화면(리더)에선 숨긴다', () => {
    setMatch(true);
    const { container } = renderWithProviders(<MobileTabBar />, { at: '/read/abc' });
    expect(container).toBeEmptyDOMElement();
  });
});
