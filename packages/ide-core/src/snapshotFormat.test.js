import { describe, it, expect } from 'vitest';
import { formatSnapshotTimestamp, formatSnapshotLabel } from './snapshotFormat.js';

describe('formatSnapshotTimestamp', () => {
  it('ISO 문자열에서 초 단위를 생략하고 공백으로 구분한다', () => {
    expect(formatSnapshotTimestamp('2026-07-08T10:15:42')).toBe('2026-07-08 10:15');
  });

  it('빈 값/undefined/null 은 빈 문자열', () => {
    expect(formatSnapshotTimestamp(null)).toBe('');
    expect(formatSnapshotTimestamp(undefined)).toBe('');
    expect(formatSnapshotTimestamp('')).toBe('');
  });
});

describe('formatSnapshotLabel', () => {
  it('라벨이 없으면(자동 스냅샷, null) "자동 저장"으로 표시', () => {
    expect(formatSnapshotLabel(null)).toBe('자동 저장');
    expect(formatSnapshotLabel(undefined)).toBe('자동 저장');
    expect(formatSnapshotLabel('')).toBe('자동 저장');
  });

  it('라벨이 있으면(수동 스냅샷) 그대로 노출', () => {
    expect(formatSnapshotLabel('복원 전 자동')).toBe('복원 전 자동');
    expect(formatSnapshotLabel('체크포인트')).toBe('체크포인트');
  });
});
