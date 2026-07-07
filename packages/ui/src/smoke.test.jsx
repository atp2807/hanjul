// 인프라 스모크 — vitest+jsdom+@testing-library/react 셋업이 이 패키지에서 실제로 도는지만
// 증명한다. 본 컴포넌트별 테스트 스위트는 W4 에서 추가.
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { Button } from './Button.jsx';

describe('@hanjul/ui 인프라 스모크', () => {
  it('Button 이 렌더된다', () => {
    render(<Button>확인</Button>);
    expect(screen.getByText('확인')).toBeInTheDocument();
  });
});
