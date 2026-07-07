import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { renderWithProviders } from '@hanjul/test-utils';
import { NotFoundPage } from './NotFoundPage';

describe('NotFoundPage', () => {
  it('404와 홈 링크를 보여준다', () => {
    renderWithProviders(<NotFoundPage />);
    expect(screen.getByText('404')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /서점으로/ })).toHaveAttribute('href', '/');
  });
});
