import { describe, expect, it, vi } from 'vitest';

import { mockApiClient } from '@hanjul/test-utils';
import { apiClient } from '../../services/api/api_client';
import { pdfToNeutral } from './pdf_import';

vi.mock('../../services/api/api_client', () => ({
  apiClient: mockApiClient(),
}));

describe('pdfToNeutral', () => {
  it('POST /import/pdf-parse 로 파일 업로드 후 서버 중립 doc 반환', async () => {
    const neutral = {
      blocks: [
        { type: 'h1', spans: [{ text: '제목', marks: [] }] },
        { type: 'p', spans: [{ text: '본문 ', marks: [] }, { text: '굵게', marks: ['strong'] }] },
      ],
    };
    apiClient.upload.mockResolvedValue(neutral);

    const file = new File([new Uint8Array([1, 2, 3])], 'manuscript.pdf', { type: 'application/pdf' });
    const result = await pdfToNeutral(file);

    expect(apiClient.upload).toHaveBeenCalledTimes(1);
    const [path, fd] = apiClient.upload.mock.calls[0];
    expect(path).toBe('/import/pdf-parse');
    expect(fd).toBeInstanceOf(FormData);
    expect(fd.get('file')).toBe(file);
    expect(result).toEqual(neutral);
  });
});
