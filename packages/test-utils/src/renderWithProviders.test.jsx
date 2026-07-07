import { screen } from '@testing-library/react';
import { useParams } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { renderWithProviders } from './renderWithProviders.jsx';

function Hello() {
  return <div>hello</div>;
}

function ShowParam() {
  const { id } = useParams();
  return <div data-testid="param">{id}</div>;
}

describe('renderWithProviders', () => {
  it('router=false 면 라우터 없이 그냥 render(ui)', () => {
    renderWithProviders(<Hello />, { router: false });
    expect(screen.getByText('hello')).toBeInTheDocument();
  });

  it('path 없이 router=true(기본) 면 MemoryRouter 로만 감싸고 ui 를 그대로 렌더', () => {
    renderWithProviders(<Hello />);
    expect(screen.getByText('hello')).toBeInTheDocument();
  });

  it('path+at 지정 시 <Routes><Route> 로 감싸 useParams 가 at 경로에서 값을 뽑는다', () => {
    renderWithProviders(<ShowParam />, { path: '/doc/:id', at: '/doc/d1' });
    expect(screen.getByTestId('param')).toHaveTextContent('d1');
  });
});
