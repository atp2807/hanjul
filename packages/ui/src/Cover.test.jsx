import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { Cover } from './Cover.jsx';

// lr-ca34f579 ③ — title은 그라데이션 시드(예: UUID)로, alt는 스크린리더용 텍스트로 분리해서 쓸 수 있어야 한다.
describe('Cover 접근성(alt override)', () => {
  it('alt 생략 시 기존처럼 title이 그대로 이미지 alt가 된다(하위호환)', () => {
    render(<Cover url="/x.jpg" title="어느 날 갑자기" />);
    expect(screen.getByRole('img', { name: '어느 날 갑자기' })).toBeInTheDocument();
  });

  it('alt를 넘기면 title(시드) 대신 alt가 이미지 alt로 쓰인다', () => {
    render(<Cover url="/x.jpg" title="uuid-1234" alt="어느 날 갑자기" />);
    const img = screen.getByRole('img', { name: '어느 날 갑자기' });
    expect(img).toHaveAttribute('src', '/x.jpg');
    expect(screen.queryByAltText('uuid-1234')).not.toBeInTheDocument();
  });

  it('placeholder(label=false)에서 title만 넘기면(UUID 등) 접근성 이름도 그 값이 된다 — alt로 override 필요', () => {
    render(<Cover title="uuid-1234" label={false} width={38} />);
    // alt override 없이 label=false만 쓰면 title이 그대로 접근성 이름으로 샌다(구 버그 재현) — 그래서 alt override가 필요.
    expect(screen.getByRole('img', { name: 'uuid-1234' })).toBeInTheDocument();
  });

  it('placeholder + alt override → 접근성 이름이 사람이 읽을 텍스트가 된다', () => {
    render(<Cover title="uuid-1234" alt="실제 책 제목" label={false} width={38} />);
    expect(screen.getByRole('img', { name: '실제 책 제목' })).toBeInTheDocument();
    expect(screen.queryByRole('img', { name: 'uuid-1234' })).not.toBeInTheDocument();
  });

  it('title/alt 둘 다 없는 placeholder(label=false)는 장식으로 간주해 접근성 트리에서 숨긴다', () => {
    render(<Cover label={false} width={38} data-testid="cover" />);
    expect(screen.getByTestId('cover')).toHaveAttribute('aria-hidden', 'true');
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
  });

  it('label=true(기본)는 제목이 눈에 보이는 텍스트라 role/aria 오버라이드가 필요 없다', () => {
    render(<Cover title="어느 날 갑자기" />);
    expect(screen.getByText('어느 날 갑자기')).toBeInTheDocument();
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
  });
});
