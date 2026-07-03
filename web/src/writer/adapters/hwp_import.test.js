import { describe, expect, it, vi } from 'vitest';

import { apiClient } from '../../services/api/api_client';
import { hwpToNeutral } from './hwp_import';

vi.mock('../../services/api/api_client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), put: vi.fn(), del: vi.fn(), upload: vi.fn(), download: vi.fn() },
}));

describe('writer/adapters/hwp_import', () => {
  it('파일을 FormData로 감싸 /import/hwp-parse 로 업로드한다', async () => {
    apiClient.upload.mockResolvedValue({ blocks: [{ type: 'p', spans: [{ text: '가져온 문단', marks: [] }] }] });
    const file = new File(['dummy'], 'sample.hwp');

    const result = await hwpToNeutral(file);

    expect(apiClient.upload).toHaveBeenCalledWith('/import/hwp-parse', expect.any(FormData));
    const fd = apiClient.upload.mock.calls[0][1];
    expect(fd.get('file')).toBe(file);
    expect(result.blocks).toHaveLength(1);
  });

  it('서버 에러(422 등)를 그대로 전파한다', async () => {
    const err = new Error('HWP 파일을 읽을 수 없어요.');
    err.status = 422;
    apiClient.upload.mockRejectedValue(err);

    await expect(hwpToNeutral(new File(['x'], 'broken.hwp'))).rejects.toThrow('HWP 파일을 읽을 수 없어요.');
  });
});
