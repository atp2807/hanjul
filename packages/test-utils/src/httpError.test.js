import { describe, expect, it } from 'vitest';

import { httpError } from './httpError.js';

describe('httpError', () => {
  it('detail 있으면 message=detail, status/detail 둘 다 설정', () => {
    const err = httpError(422, '이미 존재하는 이메일입니다.');
    expect(err).toBeInstanceOf(Error);
    expect(err.status).toBe(422);
    expect(err.detail).toBe('이미 존재하는 이메일입니다.');
    expect(err.message).toBe('이미 존재하는 이메일입니다.');
  });

  it('detail 없으면(기본 null) message 는 `API {status}` 로 대체, detail 은 null 유지', () => {
    const err = httpError(404);
    expect(err.status).toBe(404);
    expect(err.detail).toBeNull();
    expect(err.message).toBe('API 404');
  });
});
