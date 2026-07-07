import { describe, expect, it, vi } from 'vitest';

import { mockApiClient } from '@hanjul/test-utils';
import { apiClient } from '../../services/api/api_client';
import { hwpToNeutral } from './hwp_import';

vi.mock('../../services/api/api_client', () => ({
  apiClient: mockApiClient(),
}));

describe('hwpToNeutral', () => {
  it('FormData 에 file 담아 /import/hwp-parse 로 upload → {blocks} 반환', async () => {
    const doc = { blocks: [{ type: 'p', spans: [{ text: '첫 문단', marks: [] }] }] };
    apiClient.upload.mockResolvedValueOnce(doc);

    const file = new File([new Uint8Array([1, 2, 3])], 'manuscript.hwpx');
    const result = await hwpToNeutral(file);

    expect(result).toEqual(doc);
    expect(apiClient.upload).toHaveBeenCalledTimes(1);
    const [path, fd] = apiClient.upload.mock.calls[0];
    expect(path).toBe('/import/hwp-parse');
    expect(fd).toBeInstanceOf(FormData);
    expect(fd.get('file')).toBe(file);
  });

  it('서버 에러(예: PDF 변환 안내)를 그대로 전파', async () => {
    apiClient.upload.mockRejectedValueOnce(
      new Error('HWP 파일을 읽을 수 없어요. PDF로 변환한 후 다시 업로드해보세요.'),
    );
    const file = new File([new Uint8Array([0])], 'broken.hwpx');
    await expect(hwpToNeutral(file)).rejects.toThrow(/PDF로 변환/);
  });
});
