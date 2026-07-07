import { describe, it, expect } from 'vitest';
import { nextStatus, moveChapter, STATUS_CYCLE } from './chapterOrder.js';

describe('nextStatus', () => {
  it('DRAFT → REVISING → DONE → DRAFT 순으로 순환한다', () => {
    expect(nextStatus('DRAFT')).toBe('REVISING');
    expect(nextStatus('REVISING')).toBe('DONE');
    expect(nextStatus('DONE')).toBe('DRAFT');
  });

  it('알 수 없는 값/undefined 는 첫 상태(DRAFT)로 리셋한다', () => {
    expect(nextStatus('WHATEVER')).toBe('DRAFT');
    expect(nextStatus(undefined)).toBe('DRAFT');
  });

  it('STATUS_CYCLE 순서를 그대로 따른다', () => {
    expect(STATUS_CYCLE).toEqual(['DRAFT', 'REVISING', 'DONE']);
  });
});

describe('moveChapter', () => {
  it('드래그한 항목을 대상 항목 바로 앞으로 옮긴다(기본 before:true)', () => {
    expect(moveChapter(['a', 'b', 'c', 'd'], 'd', 'b')).toEqual(['a', 'd', 'b', 'c']);
  });

  it('before:false 면 대상 항목 바로 뒤로 옮긴다', () => {
    expect(moveChapter(['a', 'b', 'c', 'd'], 'a', 'c', { before: false })).toEqual(['b', 'c', 'a', 'd']);
  });

  it('맨 앞으로 옮기기', () => {
    expect(moveChapter(['a', 'b', 'c'], 'c', 'a')).toEqual(['c', 'a', 'b']);
  });

  it('맨 뒤로 옮기기(마지막 원소 뒤)', () => {
    expect(moveChapter(['a', 'b', 'c'], 'a', 'c', { before: false })).toEqual(['b', 'c', 'a']);
  });

  it('숫자 id 도 동일하게 동작하고 원소 집합/길이를 보존한다', () => {
    const ids = [1, 2, 3, 4, 5];
    const moved = moveChapter(ids, 5, 1);
    expect(moved).toHaveLength(5);
    expect([...moved].sort()).toEqual([1, 2, 3, 4, 5]);
  });

  it('같은 id 를 드래그/드롭하면 원본과 순서가 같은 새 배열을 반환한다(불변성)', () => {
    const ids = ['x', 'y'];
    const result = moveChapter(ids, 'x', 'x');
    expect(result).toEqual(ids);
    expect(result).not.toBe(ids);
  });

  it('존재하지 않는 id 가 섞이면 원본 순서를 그대로(새 배열로) 반환한다', () => {
    const ids = ['a', 'b', 'c'];
    expect(moveChapter(ids, 'z', 'b')).toEqual(ids);
    expect(moveChapter(ids, 'a', 'z')).toEqual(ids);
  });

  it('원본 배열을 변경하지 않는다', () => {
    const ids = ['a', 'b', 'c'];
    moveChapter(ids, 'c', 'a');
    expect(ids).toEqual(['a', 'b', 'c']);
  });
});
