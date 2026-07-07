import { beforeEach, describe, expect, it, vi } from 'vitest';

import { mockApiClient } from '@hanjul/test-utils';
import { apiClient } from './api_client';
import { exportDocx, exportEpub, uploadMedia } from './docs';

vi.mock('./api_client', () => ({
  apiClient: mockApiClient(),
  getToken: vi.fn(),
  apiBase: '',
}));

describe('services/api/docs', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // 결함 1 회귀 가드: 백엔드 MediaResponse 는 camelCase(displayUrl/thumbUrl) 로 응답하는데
  // juldoc 에디터 코어(packages/doc editor.js:339)는 snake_case(display_url) 를 읽는다.
  // uploadMedia() 가 경계에서 매핑하지 않으면 display_url 이 undefined 로 빠져 원본 폴백된다.
  it('uploadMedia → 백엔드 camelCase(MediaResponse) 를 juldoc 코어 snake_case 계약으로 매핑', async () => {
    apiClient.upload.mockResolvedValue({
      url: '/media/orig123',
      displayUrl: '/media/disp123',
      thumbUrl: '/media/thumb123',
      bytes: 12345,
      contentType: 'image/webp',
      width: 800,
      height: 600,
    });
    const file = new File(['x'], 'a.png', { type: 'image/png' });
    const res = await uploadMedia(file);
    // eslint-disable-next-line vitest/valid-expect -- @vitest/eslint-plugin 오탐: expect.any()가 중첩 인자로 쓰일 때 modifier로 오인
    expect(apiClient.upload).toHaveBeenCalledWith('/media', expect.any(FormData));
    expect(res).toEqual({
      url: '/media/orig123',
      display_url: '/media/disp123',
      thumb_url: '/media/thumb123',
      bytes: 12345,
      content_type: 'image/webp',
      width: 800,
      height: 600,
    });
  });

  // 결함 3 회귀 가드: <a href> 방식은 Authorization 을 못 실어 mine 문서 수출이 403 났다.
  // exportEpub/exportDocx 는 apiClient.download(인증 Bearer 첨부) 를 거쳐야 한다.
  it('exportEpub → apiClient.download(문서 export 경로, 파일명) 로 인증 다운로드', async () => {
    apiClient.download.mockResolvedValue();
    await exportEpub('d1', '내 보고서');
    expect(apiClient.download).toHaveBeenCalledWith('/documents/d1/export/epub', '내 보고서.epub');
  });

  it('exportDocx → apiClient.download(문서 export 경로, 파일명) 로 인증 다운로드', async () => {
    apiClient.download.mockResolvedValue();
    await exportDocx('d1', '내 보고서');
    expect(apiClient.download).toHaveBeenCalledWith('/documents/d1/export/docx', '내 보고서.docx');
  });

  it('exportEpub → title 없으면 id 로 파일명 폴백', async () => {
    apiClient.download.mockResolvedValue();
    await exportEpub('d1');
    expect(apiClient.download).toHaveBeenCalledWith('/documents/d1/export/epub', 'd1.epub');
  });
});
