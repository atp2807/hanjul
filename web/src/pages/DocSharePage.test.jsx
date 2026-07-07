import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import * as docsApi from '../services/api/docs';
import { DocSharePage } from './DocSharePage';

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
    <MemoryRouter initialEntries={['/doc/s/tok1']}>
      <Routes><Route path="/doc/s/:token" element={<DocSharePage />} /></Routes>
    </MemoryRouter>,
  );
}

describe('DocSharePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    docsApi.getShareHtml.mockResolvedValue('<article data-juldoc="1"><p>공유본문</p></article>');
    docsApi.shareExportEpubUrl.mockReturnValue('http://api/shares/tok1/export/epub');
    docsApi.shareExportDocxUrl.mockReturnValue('http://api/shares/tok1/export/docx');
  });

  it('VIEW 권한 → 리더 전용(편집 토글 없음)', async () => {
    docsApi.getShareMeta.mockResolvedValue({ title: '공유문서', capability: 'view' });
    renderPage();
    expect(await screen.findByTestId('doc-reader')).toHaveTextContent('공유본문');
    expect(screen.getByText('읽기 전용')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '편집' })).not.toBeInTheDocument();
  });

  it('EDIT 권한 → 에디터 시작 + 읽기/편집 토글 노출', async () => {
    docsApi.getShareMeta.mockResolvedValue({ title: '공유문서', capability: 'edit' });
    renderPage();
    expect(await screen.findByTestId('doc-editor')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '편집' })).toBeInTheDocument();
    expect(screen.getByText('편집 가능')).toBeInTheDocument();
  });

  it('EDIT 저장 → saveShareHtml(token, outer) 호출', async () => {
    docsApi.getShareMeta.mockResolvedValue({ title: '공유문서', capability: 'edit' });
    docsApi.saveShareHtml.mockResolvedValue(null);
    renderPage();
    fireEvent.click(await screen.findByText('발화-저장'));
    await waitFor(() =>
      expect(docsApi.saveShareHtml).toHaveBeenCalledWith('tok1', '<article data-juldoc="1">편집됨</article>'),
    );
  });

  it('EXPORT 권한 → 리더 + EPUB/DOCX 다운로드 버튼', async () => {
    docsApi.getShareMeta.mockResolvedValue({ title: '공유문서', capability: 'export' });
    renderPage();
    expect(await screen.findByTestId('doc-reader')).toBeInTheDocument();
    expect(screen.getByText('EPUB').closest('a')).toHaveAttribute('href', 'http://api/shares/tok1/export/epub');
    expect(screen.getByText('DOCX').closest('a')).toHaveAttribute('href', 'http://api/shares/tok1/export/docx');
  });

  it('회수/부재(404) → 안내 문구', async () => {
    const err = new Error('gone'); err.status = 404;
    docsApi.getShareMeta.mockRejectedValue(err);
    docsApi.getShareHtml.mockRejectedValue(err);
    renderPage();
    expect(await screen.findByText('링크를 찾을 수 없습니다')).toBeInTheDocument();
  });
});
