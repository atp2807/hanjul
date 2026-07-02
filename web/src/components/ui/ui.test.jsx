import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { Badge, Button, Card, Chip, Field, PageHeader, Stat } from './index';

describe('디자인 시스템 컴포넌트', () => {
  it('Button: kind별 렌더 + 클릭', () => {
    const onClick = vi.fn();
    render(<Button kind="primary" onClick={onClick}>구매</Button>);
    const btn = screen.getByRole('button', { name: '구매' });
    btn.click();
    expect(onClick).toHaveBeenCalled();
  });

  it('Badge: tone별 텍스트', () => {
    render(<Badge tone="mint">추천</Badge>);
    expect(screen.getByText('추천')).toBeInTheDocument();
  });

  it('Card: 자식 렌더', () => {
    render(<Card bordered>내용</Card>);
    expect(screen.getByText('내용')).toBeInTheDocument();
  });

  it('Chip: active 상태', () => {
    render(<Chip active>전체</Chip>);
    expect(screen.getByRole('button', { name: '전체' })).toBeInTheDocument();
  });

  it('Field: 라벨 + 입력', () => {
    render(<Field label="이메일" placeholder="me@x.com" />);
    expect(screen.getByText('이메일')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('me@x.com')).toBeInTheDocument();
  });

  it('PageHeader: 제목 + 부제', () => {
    render(<PageHeader title="정산" subtitle="출금 신청" />);
    expect(screen.getByRole('heading', { name: '정산' })).toBeInTheDocument();
    expect(screen.getByText('출금 신청')).toBeInTheDocument();
  });

  it('Stat: 값 + 라벨', () => {
    render(<Stat label="판매 부수" value="12권" />);
    expect(screen.getByText('12권')).toBeInTheDocument();
    expect(screen.getByText('판매 부수')).toBeInTheDocument();
  });
});
