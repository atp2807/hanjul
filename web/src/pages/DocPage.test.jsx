import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import * as docsApi from '../services/api/docs';
import { DocPage } from './DocPage';

vi.mock('../services/api/docs');
vi.mock('@hanjul/doc', () => ({
  DocReader: ({ html }) => <div data-testid="doc-reader">{html}</div>,
  DocEditor: ({ html, onSave }) => (
    <div data-testid="doc-editor">
      <button onClick={() => onSave('<article data-juldoc="1">편집됨</article>')}>발화-저장</button>
      <span>{html}</span>
    </div>
  ),
}));

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/doc/d1']}>
      <Routes><Route path="/doc/:id" element={<DocPage />} /></Routes>
    </MemoryRouter>,
  );
}

describe('DocPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    docsApi.getDocument.mockResolvedValue({ id: 'd1', title: '내 보고서', format: 'pdf', mine: true });
    docsApi.getDocumentHtml.mockResolvedValue('<article data-juldoc="1"><p>본문</p></article>');
    docsApi.listShares.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 50 });
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: vi.fn().mockResolvedValue() }, configurable: true,
    });
  });

  it('로드 → 읽기(DocReader) 기본 렌더 + 제목', async () => {
    renderPage();
    expect(await screen.findByText('내 보고서')).toBeInTheDocument();
    expect(await screen.findByTestId('doc-reader')).toHaveTextContent('본문');
    expect(screen.getByText('내 문서')).toBeInTheDocument(); // mine 배지
  });

  it('로드 실패 → 에러 안내', async () => {
    docsApi.getDocument.mockRejectedValue(new Error('boom'));
    renderPage();
    expect(await screen.findByText('문서를 불러오지 못했어요.')).toBeInTheDocument();
  });

  it('편집 토글 → DocEditor 로 전환', async () => {
    renderPage();
    await screen.findByTestId('doc-reader');
    fireEvent.click(screen.getByRole('button', { name: '편집' }));
    expect(await screen.findByTestId('doc-editor')).toBeInTheDocument();
    expect(screen.queryByTestId('doc-reader')).not.toBeInTheDocument();
  });

  it('편집 중 저장 → saveDocumentHtml(id, outer) 호출', async () => {
    docsApi.saveDocumentHtml.mockResolvedValue({ id: 'd1' });
    renderPage();
    await screen.findByTestId('doc-reader');
    fireEvent.click(screen.getByRole('button', { name: '편집' }));
    fireEvent.click(await screen.findByText('발화-저장'));
    await waitFor(() =>
      expect(docsApi.saveDocumentHtml).toHaveBeenCalledWith('d1', '<article data-juldoc="1">편집됨</article>'),
    );
  });

  it('EPUB/DOCX 수출 버튼 → exportEpub/exportDocx(id, title) 인증 다운로드 호출(href 아님)', async () => {
    docsApi.exportEpub.mockResolvedValue();
    docsApi.exportDocx.mockResolvedValue();
    renderPage();
    await screen.findByText('내 보고서');
    expect(screen.getByText('EPUB').closest('a')).toBeNull(); // <a href> 아님 — 인증 필요해 apiClient.download 경유
    fireEvent.click(screen.getByText('EPUB'));
    await waitFor(() => expect(docsApi.exportEpub).toHaveBeenCalledWith('d1', '내 보고서'));
    fireEvent.click(screen.getByText('DOCX'));
    await waitFor(() => expect(docsApi.exportDocx).toHaveBeenCalledWith('d1', '내 보고서'));
  });

  it('EPUB 수출 실패(403, mine 문서 인증 누락 회귀) → 안내 문구', async () => {
    const err = new Error('403'); err.status = 403;
    docsApi.exportEpub.mockRejectedValue(err);
    renderPage();
    await screen.findByText('내 보고서');
    fireEvent.click(screen.getByText('EPUB'));
    expect(await screen.findByText('소유자만 내보낼 수 있어요.')).toBeInTheDocument();
  });

  it('공유 패널 → listShares 조회 + 발급 링크 목록(hanjul /doc/s/ 경로)', async () => {
    docsApi.listShares.mockResolvedValue({
      items: [{ id: 's1', token: 'tok1', capability: 'view', revoked: false }],
      total: 1, page: 1, page_size: 50,
    });
    renderPage();
    await screen.findByText('내 보고서');
    fireEvent.click(screen.getByRole('button', { name: '공유' }));
    await waitFor(() => expect(docsApi.listShares).toHaveBeenCalledWith('d1'));
    expect(await screen.findByText(/\/doc\/s\/tok1/)).toBeInTheDocument();
  });

  it('공유 발급 → createShare(cap) 호출 후 목록 갱신', async () => {
    docsApi.createShare.mockResolvedValue({ id: 's9', token: 'tokNew', capability: 'edit', revoked: false });
    renderPage();
    await screen.findByText('내 보고서');
    fireEvent.click(screen.getByRole('button', { name: '공유' }));
    await waitFor(() => expect(docsApi.listShares).toHaveBeenCalled());
    fireEvent.change(screen.getByLabelText('공유 권한'), { target: { value: 'edit' } });
    fireEvent.click(screen.getByRole('button', { name: '링크 발급' }));
    await waitFor(() => expect(docsApi.createShare).toHaveBeenCalledWith('d1', 'edit'));
  });

  it('공유 회수 → revokeShare(shareId) 호출', async () => {
    docsApi.listShares.mockResolvedValue({
      items: [{ id: 's1', token: 'tok1', capability: 'view', revoked: false }],
      total: 1, page: 1, page_size: 50,
    });
    docsApi.revokeShare.mockResolvedValue(null);
    renderPage();
    await screen.findByText('내 보고서');
    fireEvent.click(screen.getByRole('button', { name: '공유' }));
    fireEvent.click(await screen.findByRole('button', { name: '회수' }));
    await waitFor(() => expect(docsApi.revokeShare).toHaveBeenCalledWith('s1'));
  });
});
