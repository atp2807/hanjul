import { fireEvent, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders, httpError } from '@hanjul/test-utils';
import * as books from '../services/api/books';
import * as contentRating from '../services/api/contentRating';
import * as studio from '../services/api/studio';
import { StudioEditorPage } from './StudioEditorPage';

vi.mock('../services/api/books');
vi.mock('../services/api/studio');
vi.mock('../services/api/contentRating');

const CRITERIA = {
  tiers: ['ALL', 'AGE12', 'AGE15', 'AGE18'],
  tierLabels: { ALL: '전체이용가', AGE12: '12세 이용가', AGE15: '15세 이용가', AGE18: '18세 이용가' },
  categories: [
    { key: 'theme', label: '주제', guide: { ALL: 'a', AGE12: 'b', AGE15: 'c', AGE18: 'd' } },
    { key: 'violence', label: '폭력성', guide: { ALL: 'a', AGE12: 'b', AGE15: 'c', AGE18: 'd' } },
    { key: 'sexual', label: '선정성', guide: { ALL: 'a', AGE12: 'b', AGE15: 'c', AGE18: 'd' } },
    { key: 'language', label: '언어', guide: { ALL: 'a', AGE12: 'b', AGE15: 'c', AGE18: 'd' } },
    { key: 'drug', label: '약물', guide: { ALL: 'a', AGE12: 'b', AGE15: 'c', AGE18: 'd' } },
    { key: 'gambling', label: '사행성', guide: { ALL: 'a', AGE12: 'b', AGE15: 'c', AGE18: 'd' } },
    { key: 'imitation_risk', label: '모방위험', guide: { ALL: 'a', AGE12: 'b', AGE15: 'c', AGE18: 'd' } },
    { key: 'discrimination', label: '차별', guide: { ALL: 'a', AGE12: 'b', AGE15: 'c', AGE18: 'd' } },
  ],
};

function renderEditor() {
  return renderWithProviders(<StudioEditorPage />, { path: '/studio/:id', at: '/studio/b1' });
}

beforeEach(() => {
  vi.clearAllMocks();
  studio.getMyBooks.mockResolvedValue({ items: [{ id: 'b1', isbn: '9788912345678' }] });
  contentRating.getCriteria.mockResolvedValue(CRITERIA);
});

describe('StudioEditorPage', () => {
  it('초안: ISBN·즉시출간·예약발행을 노출하고 배포 섹션은 숨긴다', async () => {
    books.getBookContent.mockResolvedValue({
      id: 'b1', title: '내 책', status: 'DRAFT', priceAmt: 9000, chapters: [],
    });
    renderEditor();
    expect(await screen.findByText('내 책')).toBeInTheDocument();
    expect(screen.getByDisplayValue('9788912345678')).toBeInTheDocument(); // ISBN 로드
    expect(screen.getByText('즉시 출간')).toBeInTheDocument();
    expect(screen.getByText('예약 발행')).toBeInTheDocument();
    expect(screen.queryByText('서점 배포')).not.toBeInTheDocument(); // 미출판
  });

  it('표지 이미지 업로드 → 미리보기 이미지가 뜬다', async () => {
    books.getBookContent.mockResolvedValue({
      id: 'b1', title: '내 책', status: 'DRAFT', priceAmt: 0, chapters: [],
    });
    studio.uploadCover.mockResolvedValue({ coverUrl: 'data:image/svg+xml;utf8,<svg/>' });

    const { container } = renderEditor();
    await screen.findByText('내 책');
    const file = new File(['x'], 'cover.png', { type: 'image/png' });
    fireEvent.change(container.querySelector('input[type="file"]'), { target: { files: [file] } });

    await waitFor(() => expect(studio.uploadCover).toHaveBeenCalledWith('b1', file));
    expect(await screen.findByRole('img', { name: '표지' })).toBeInTheDocument();
  });

  it('출판본: 서점 배포 → 전송됨 이력이 다시 로드된다', async () => {
    books.getBookContent.mockResolvedValue({
      id: 'b1', title: '내 책', status: 'PUBLISHED', priceAmt: 9000, chapters: [],
    });
    studio.getDistributions
      .mockResolvedValueOnce([])
      .mockResolvedValue([
        { id: 'd1', channel: 'KYOBO', status: 'SENT', message: null, createdAt: '2026-06-18T00:00:00Z' },
      ]);
    studio.distributeBook.mockResolvedValue({ status: 'SENT', channel: 'KYOBO' });

    renderEditor();
    fireEvent.click(await screen.findByText('배포 전송'));

    await waitFor(() => expect(studio.distributeBook).toHaveBeenCalledWith('b1', 'KYOBO'));
    expect(await screen.findByText('전송됨')).toBeInTheDocument();
  });

  it('배포 실패(status!=SENT) → 실패 메시지 표시', async () => {
    books.getBookContent.mockResolvedValue({
      id: 'b1', title: '내 책', status: 'PUBLISHED', priceAmt: 9000, chapters: [],
    });
    studio.getDistributions.mockResolvedValue([]);
    studio.distributeBook.mockResolvedValue({ status: 'FAILED', message: '채널 오류' });

    renderEditor();
    fireEvent.click(await screen.findByText('배포 전송'));
    expect(await screen.findByText(/배포 실패: 채널 오류/)).toBeInTheDocument();
  });

  it('책 로드 실패 → 에러 화면 (빈 목록 아님)', async () => {
    books.getBookContent.mockRejectedValue(new Error('네트워크 오류'));
    renderEditor();
    expect(await screen.findByText('네트워크 오류')).toBeInTheDocument();
  });

  it('가격 저장(run 성공 경로) → 메시지 표시 + 재로드', async () => {
    books.getBookContent.mockResolvedValue({ id: 'b1', title: '내 책', status: 'DRAFT', priceAmt: 5000, chapters: [] });
    studio.setBookPrice.mockResolvedValue(null);
    renderEditor();

    await screen.findByText('내 책');
    fireEvent.click(screen.getByRole('button', { name: '가격 저장' }));
    await waitFor(() => expect(studio.setBookPrice).toHaveBeenCalledWith('b1', 5000));
    expect(await screen.findByText('가격이 저장됐어요.')).toBeInTheDocument();
    expect(books.getBookContent).toHaveBeenCalledTimes(2); // 최초 + 저장 후 재로드
  });

  it('ISBN 저장 실패(run 실패 경로) → 에러 메시지', async () => {
    books.getBookContent.mockResolvedValue({ id: 'b1', title: '내 책', status: 'DRAFT', priceAmt: 0, chapters: [] });
    studio.setIsbn.mockRejectedValue(new Error('저장 실패'));
    renderEditor();

    await screen.findByText('내 책');
    fireEvent.click(screen.getByRole('button', { name: 'ISBN 저장' }));
    expect(await screen.findByText('저장 실패')).toBeInTheDocument();
  });

  it('원고 추가 — 빈 텍스트면 API 호출 안 함, 입력 있으면 추가 후 비움', async () => {
    books.getBookContent.mockResolvedValue({ id: 'b1', title: '내 책', status: 'DRAFT', priceAmt: 0, chapters: [] });
    studio.importText.mockResolvedValue({ blockCount: 3 });
    renderEditor();

    await screen.findByText('내 책');
    const addBtn = screen.getByRole('button', { name: '장 추가' });
    fireEvent.click(addBtn); // 빈 텍스트
    expect(studio.importText).not.toHaveBeenCalled();

    const textarea = screen.getByPlaceholderText(/장 제목/);
    fireEvent.change(textarea, { target: { value: '# 1장\n\n본문' } });
    fireEvent.click(addBtn);
    await waitFor(() => expect(studio.importText).toHaveBeenCalledWith('b1', '# 1장\n\n본문'));
    expect(await screen.findByText('3개 블록이 새 장으로 추가됐어요.')).toBeInTheDocument();
    expect(textarea).toHaveValue('');
  });

  it('표지 업로드 실패(422) → 형식 안내, 그 외는 원문 메시지', async () => {
    books.getBookContent.mockResolvedValue({ id: 'b1', title: '내 책', status: 'DRAFT', priceAmt: 0, chapters: [] });
    studio.uploadCover.mockRejectedValue(httpError(422));
    const { container } = renderEditor();

    await screen.findByText('내 책');
    const file = new File(['x'], 'cover.png', { type: 'image/png' });
    fireEvent.change(container.querySelector('input[type="file"]'), { target: { files: [file] } });
    expect(await screen.findByText('이미지 파일(PNG·JPG·WebP, 5MB 이하)만 올릴 수 있어요.')).toBeInTheDocument();
  });

  it('예약 발행 — 시각 미선택 시 검증 에러, 선택 시 예약', async () => {
    books.getBookContent.mockResolvedValue({ id: 'b1', title: '내 책', status: 'DRAFT', priceAmt: 0, chapters: [] });
    studio.schedulePublish.mockResolvedValue(null);
    renderEditor();

    await screen.findByText('내 책');
    fireEvent.click(screen.getByRole('button', { name: '예약 발행' }));
    expect(await screen.findByText('발행 시각을 선택하세요.')).toBeInTheDocument();
    expect(studio.schedulePublish).not.toHaveBeenCalled();

    // 기간 할인 섹션에도 datetime-local 입력이 있어 마지막(출판 섹션의 예약 발행) 것을 선택
    const inputs = document.querySelectorAll('input[type="datetime-local"]');
    const input = inputs[inputs.length - 1];
    fireEvent.change(input, { target: { value: '2026-08-01T10:00' } });
    fireEvent.click(screen.getByRole('button', { name: '예약 발행' }));
    await waitFor(() => expect(studio.schedulePublish).toHaveBeenCalledWith('b1', new Date('2026-08-01T10:00').toISOString()));
  });

  it('소개문 추천 → 설명란에 반영', async () => {
    books.getBookContent.mockResolvedValue({ id: 'b1', title: '내 책', status: 'DRAFT', priceAmt: 0, chapters: [] });
    studio.suggestBlurb.mockResolvedValue({ blurb: 'AI가 뽑은 소개' });
    renderEditor();

    await screen.findByText('내 책');
    fireEvent.click(screen.getByRole('button', { name: '소개문 추천' }));
    await waitFor(() => expect(screen.getByPlaceholderText('책 소개 (스토어 상세에 노출)')).toHaveValue('AI가 뽑은 소개'));
    expect(await screen.findByText(/본문에서 소개문을 추천했어요/)).toBeInTheDocument();
  });

  it('책 삭제 — 확인 취소하면 삭제 안 됨, 확인하면 삭제 후 이동', async () => {
    books.getBookContent.mockResolvedValue({ id: 'b1', title: '내 책', status: 'DRAFT', priceAmt: 0, chapters: [] });
    studio.deleteBook.mockResolvedValue(null);
    const confirmSpy = vi.spyOn(window, 'confirm');
    renderEditor();
    await screen.findByText('내 책');

    confirmSpy.mockReturnValueOnce(false);
    fireEvent.click(screen.getByRole('button', { name: '이 책 삭제' }));
    expect(studio.deleteBook).not.toHaveBeenCalled();

    confirmSpy.mockReturnValueOnce(true);
    fireEvent.click(screen.getByRole('button', { name: '이 책 삭제' }));
    await waitFor(() => expect(studio.deleteBook).toHaveBeenCalledWith('b1'));
    confirmSpy.mockRestore();
  });

  it('판매 이력 있는 책 삭제 시도(409) → 출판취소 안내', async () => {
    books.getBookContent.mockResolvedValue({ id: 'b1', title: '내 책', status: 'PUBLISHED', priceAmt: 9000, chapters: [] });
    studio.getDistributions.mockResolvedValue([]);
    studio.deleteBook.mockRejectedValue(httpError(409));
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    renderEditor();

    await screen.findByText('내 책');
    fireEvent.click(screen.getByRole('button', { name: '이 책 삭제' }));
    expect(await screen.findByText('판매 이력이 있어 삭제할 수 없어요. 출판 취소만 가능해요.')).toBeInTheDocument();
    window.confirm.mockRestore();
  });

  it('REVIEW 상태 — 심사 제출 버튼 숨김, 출판 버튼 노출·클릭 시 출판완료', async () => {
    books.getBookContent.mockResolvedValue({ id: 'b1', title: '내 책', status: 'REVIEW', priceAmt: 9000, chapters: [] });
    studio.publishBook.mockResolvedValue(null);
    renderEditor();

    await screen.findByText('내 책');
    expect(screen.queryByRole('button', { name: '심사 제출' })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '출판' }));
    await waitFor(() => expect(studio.publishBook).toHaveBeenCalledWith('b1'));
    expect(await screen.findByText('출판 완료! 스토어에 노출됩니다.')).toBeInTheDocument();
  });

  it('연령 등급 — AI 추천 클릭 후 8개 select가 추천값으로 프리필된다', async () => {
    books.getBookContent.mockResolvedValue({ id: 'b1', title: '내 책', status: 'DRAFT', priceAmt: 0, chapters: [] });
    contentRating.suggestRating.mockResolvedValue({
      contentRating: 'AGE15',
      contentRatingDetail: {
        theme: 'ALL', violence: 'AGE15', sexual: 'ALL', language: 'AGE12',
        drug: 'ALL', gambling: 'ALL', imitation_risk: 'ALL', discrimination: 'ALL',
      },
    });
    renderEditor();
    await screen.findByText('내 책');

    fireEvent.click(screen.getByRole('button', { name: 'AI로 추천받기' }));
    await waitFor(() => expect(contentRating.suggestRating).toHaveBeenCalledWith('b1'));

    // 8개 카테고리 select 렌더 + 추천값 프리필
    const selects = ['주제', '폭력성', '선정성', '언어', '약물', '사행성', '모방위험', '차별'].map(
      (label) => screen.getByRole('combobox', { name: `${label} 등급` }),
    );
    expect(selects).toHaveLength(8);
    expect(screen.getByRole('combobox', { name: '폭력성 등급' })).toHaveValue('AGE15');
    expect(screen.getByRole('combobox', { name: '언어 등급' })).toHaveValue('AGE12');
    // 최종 등급 배지 = 8개 중 최댓값 (AGE15)
    expect(screen.getByText('최종 등급: 15세 이용가')).toBeInTheDocument();
  });

  it('연령 등급 — 저장 클릭 시 8개 값 dict로 setRating 호출', async () => {
    books.getBookContent.mockResolvedValue({
      id: 'b1', title: '내 책', status: 'DRAFT', priceAmt: 0, chapters: [],
      contentRating: 'AGE18', contentRatingDetail: {
        theme: 'ALL', violence: 'ALL', sexual: 'AGE18', language: 'ALL',
        drug: 'ALL', gambling: 'ALL', imitation_risk: 'ALL', discrimination: 'ALL',
      },
    });
    contentRating.setRating.mockResolvedValue({ contentRating: 'AGE18', contentRatingDetail: {} });
    renderEditor();
    await screen.findByText('내 책');

    // 초기 프리필(content 응답) 확인
    expect(await screen.findByRole('combobox', { name: '선정성 등급' })).toHaveValue('AGE18');

    fireEvent.click(screen.getByRole('button', { name: '등급 저장' }));
    await waitFor(() => expect(contentRating.setRating).toHaveBeenCalledWith('b1', {
      theme: 'ALL', violence: 'ALL', sexual: 'AGE18', language: 'ALL',
      drug: 'ALL', gambling: 'ALL', imitation_risk: 'ALL', discrimination: 'ALL',
    }));
    expect(await screen.findByText('연령 등급이 저장됐어요.')).toBeInTheDocument();
  });
});
