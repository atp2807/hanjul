// 라우터를 씌워 렌더 — useParams/useNavigate 등을 쓰는 페이지 컴포넌트는 실제 앱처럼
// <Routes>/<Route> 안에서 그려야 하므로, 그 반복 보일러플레이트를 한 곳에 모은다.
import { render } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

/**
 * @param {import('react').ReactNode} ui 렌더할 엘리먼트 (path 지정 시 <Route element> 로 들어감)
 * @param {object} [opts]
 * @param {string} [opts.path] 라우트 path (예: '/doc/:id'). 지정하면 <Routes><Route path={path} element={ui} /></Routes> 로 감싼다.
 * @param {string} [opts.at='/'] MemoryRouter initialEntries 진입 경로 (예: '/doc/d1').
 * @param {boolean} [opts.router=true] false 면 라우터 없이 그냥 render(ui) — 라우팅과 무관한 컴포넌트용.
 * @returns {import('@testing-library/react').RenderResult}
 */
export function renderWithProviders(ui, { path, at = '/', router = true } = {}) {
  if (!router) return render(ui);

  const tree = path ? (
    <Routes>
      <Route path={path} element={ui} />
    </Routes>
  ) : ui;

  return render(<MemoryRouter initialEntries={[at]}>{tree}</MemoryRouter>);
}
