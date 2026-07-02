import { Cover } from '@hanjul/ui';

export const Placeholder = () => (
  <div style={{ width: 150 }}><Cover title="한 줄의 기록" /></div>
);
export const WithImage = () => (
  <div style={{ width: 150 }}><Cover url="https://picsum.photos/seed/hanjul/300/430" title="사진 표지" /></div>
);
export const Hero = () => (
  <div style={{ width: 190 }}>
    <Cover title="깊은 밤의 위로" radius={16} labelSize={22} style={{ boxShadow: '0 30px 50px -22px rgba(12,58,50,0.5)' }} />
  </div>
);
export const Thumbnail = () => <Cover title="따뜻한 에세이" width={44} radius={7} label={false} />;
export const ThumbnailSmall = () => <Cover title="시집" width={32} radius={5} label={false} />;
