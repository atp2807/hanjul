import { fireEvent, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders, authFixture, httpError } from '@hanjul/test-utils';
import * as docsApi from '../services/api/docs';
import { DocsPage } from './DocsPage';

vi.mock('../services/api/docs');
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async (o) => ({ ...(await o()), useNavigate: () => mockNavigate }));
let mockUser = null;
vi.mock('../auth/AuthContext', () => ({ useAuth: () => authFixture({ user: mockUser }) }));

function renderPage() {
  return renderWithProviders(<DocsPage />);
}

const LIST = {
  items: [
    { id: 'd1', title: '보고서', format: 'pdf', mine: true },
    { id: 'd2', title: '공유문서', format: 'docx', mine: false },
  ],
  total: 2,
  page: 1,
  page_size: 20,
};

describe('DocsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUser = null;
    docsApi.listDocuments.mockResolvedValue(LIST);
  });

  it('문서 목록을 보여주고 내 문서에 배지를 단다', async () => {
    renderPage();
    expect(await screen.findByText('보고서')).toBeInTheDocument();
    expect(screen.getByText('공유문서')).toBeInTheDocument();
    expect(screen.getByText('내 문서')).toBeInTheDocument(); // d1(mine)만
  });

  it('목록 로드 실패 → 에러 안내(침묵 금지)', async () => {
    docsApi.listDocuments.mockRejectedValue(new Error('network'));
    renderPage();
    expect(await screen.findByText('문서 목록을 불러오지 못했어요.')).toBeInTheDocument();
  });

  it('빈 목록 → 안내 문구', async () => {
    docsApi.listDocuments.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 });
    renderPage();
    expect(await screen.findByText(/아직 문서가 없어요/)).toBeInTheDocument();
  });

  it('빈 문서 생성 → 생성 후 편집 페이지로 이동', async () => {
    docsApi.createDocument.mockResolvedValue({ id: 'new1', title: '메모', format: 'html' });
    renderPage();
    await screen.findByText('보고서');
    fireEvent.change(screen.getByLabelText('새 문서 제목'), { target: { value: '메모' } });
    fireEvent.click(screen.getByText('빈 문서 만들기'));
    await waitFor(() => expect(docsApi.createDocument).toHaveBeenCalledWith('메모'));
    expect(mockNavigate).toHaveBeenCalledWith('/doc/new1');
  });

  it('빈 제목으로 생성하면 "제목 없음"으로 만든다', async () => {
    docsApi.createDocument.mockResolvedValue({ id: 'n2' });
    renderPage();
    await screen.findByText('보고서');
    fireEvent.click(screen.getByText('빈 문서 만들기'));
    await waitFor(() => expect(docsApi.createDocument).toHaveBeenCalledWith('제목 없음'));
  });

  it('파일 업로드 → 업로드 후 문서 페이지로 이동', async () => {
    docsApi.uploadDocument.mockResolvedValue({ id: 'up1', title: 'x.pdf', format: 'pdf' });
    const { container } = renderPage();
    await screen.findByText('보고서');
    const input = container.querySelector('input[type="file"]');
    const file = new File(['%PDF'], 'x.pdf', { type: 'application/pdf' });
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => expect(docsApi.uploadDocument).toHaveBeenCalledWith(file));
    expect(mockNavigate).toHaveBeenCalledWith('/doc/up1');
  });

  it('삭제 → deleteDocument 호출 후 목록 재조회', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    docsApi.deleteDocument.mockResolvedValue(null);
    renderPage();
    await screen.findByText('보고서');
    fireEvent.click(screen.getByLabelText('보고서 삭제'));
    await waitFor(() => expect(docsApi.deleteDocument).toHaveBeenCalledWith('d1'));
    expect(docsApi.listDocuments).toHaveBeenCalledTimes(2); // 초기 + 삭제 후
  });

  it('삭제 403 → 소유자 안내', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    docsApi.deleteDocument.mockRejectedValue(httpError(403));
    renderPage();
    await screen.findByText('보고서');
    fireEvent.click(screen.getByLabelText('보고서 삭제'));
    expect(await screen.findByText('소유자만 삭제할 수 있어요.')).toBeInTheDocument();
  });
});
