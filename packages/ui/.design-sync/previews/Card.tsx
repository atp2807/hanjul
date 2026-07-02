import { Card } from '@hanjul/ui';

export const Shadow = () => (
  <Card>
    <div style={{ fontWeight: 700, marginBottom: 6 }}>기본 카드</div>
    <div style={{ color: '#7d949c', fontSize: 14 }}>흰 배경 + 은은한 그림자</div>
  </Card>
);

export const Bordered = () => (
  <Card bordered>
    <div style={{ fontWeight: 700, marginBottom: 6 }}>테두리 카드</div>
    <div style={{ color: '#7d949c', fontSize: 14 }}>얇은 테두리 스타일</div>
  </Card>
);

export const Ink = () => (
  <Card tone="ink">
    <div style={{ fontWeight: 700, marginBottom: 6 }}>강조 카드</div>
    <div style={{ color: '#9bc6cf', fontSize: 14 }}>딥틸 배경 · 밝은 텍스트</div>
  </Card>
);
