import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { B2BPlanPage } from './B2BPlanPage';

describe('B2BPlanPage', () => {
  it('3개 플랜과 무료 안내를 렌더한다', () => {
    render(<MemoryRouter><B2BPlanPage /></MemoryRouter>);
    expect(screen.getByText('Basic')).toBeInTheDocument();
    expect(screen.getByText('Growth')).toBeInTheDocument();
    expect(screen.getByText('Enterprise')).toBeInTheDocument();
    expect(screen.getByText('가장 인기')).toBeInTheDocument();
    expect(screen.getByText(/개인 작가의 셀프 캠페인은/)).toBeInTheDocument();
  });
});
