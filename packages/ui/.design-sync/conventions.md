# 한줄 디자인 시스템 (@hanjul/ui)

한줄의 공용 UI 프리미티브. React 19 · 순수 JSX(TypeScript 없음) · **인라인 스타일 + 토큰**.

## 셋업 — 프로바이더/CSS import 불필요
컴포넌트는 self-styling(인라인 스타일)이라 별도 Provider·CSS import가 필요 없다.
컴포넌트와 토큰만 import해서 쓴다:

    import { Button, Card, T } from '@hanjul/ui';

## 스타일 관례 — CSS 클래스 없음, `T` 토큰을 인라인 style로
이 디자인 시스템은 **CSS 클래스를 쓰지 않는다.** 색·간격·폰트는 `T` 토큰 객체를 인라인 `style`로 지정한다. 컴포넌트가 아닌 자체 레이아웃 glue도 이 방식으로 맞춘다.

- 브랜드: `T.ink`(딥틸 #0e4a5c) · `T.accent` · `T.bg`(연민트 배경) · `T.surface`(흰색) · `T.inkText`(어두운 배경 위 밝은 텍스트)
- 텍스트: `T.textStrong` · `T.text` · `T.textMid` · `T.muted` · `T.faint`
- 상태: `T.ok`/`T.okBg` · `T.warn`/`T.warnBg` · `T.danger`/`T.dangerBg` · `T.info`/`T.infoBg`
- 사이드바(운영 콘솔): `T.sidebar` · `T.sidebarText`
- 반경: `T.radius.sm|md|lg|xl|card|pill` · 폰트: `T.font`(IBM Plex Sans KR)

컴포넌트 커스텀은 `style` prop으로 오버라이드:

    <Button kind="primary" style={{ marginTop: 12 }}>구매하기</Button>

## 컴포넌트 (props는 각 components/<Name>/<Name>.d.ts 참조)
- **Button** — `kind`: primary|secondary|ghost|danger, `size`: md|sm, `block`
- **Card** — `bordered`, `tone`: ink(딥틸 강조 카드)
- **Badge** — `tone`: mint|ok|danger|warn|info|neutral (mint=ok, 초록)
- **Chip** — `active` (필터 칩)
- **Field** — `label`, `as`: input|textarea
- **PageHeader** — `title`, `subtitle`, `right`(우측 액션)
- **Stat** — `label`, `value`, `color`(값 색상)

## 진실의 소스
컴포넌트 API는 `components/<Name>/<Name>.d.ts`, 토큰 `T`는 `_ds_bundle.js`에서 export된다(`window.HanjulUI.T`).

## 빌드 예시 (라이브러리 컴포넌트 + T 토큰으로 레이아웃)

    import { PageHeader, Stat, Button, T } from '@hanjul/ui';

    <div style={{ padding: 24, background: T.bg, font: T.font }}>
      <PageHeader
        title="정산·출금"
        subtitle="판매 정산금을 등록한 계좌로 출금 신청하세요."
        right={<Button size="sm">전체 보기</Button>}
      />
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
        <Stat label="총 매출" value="1,240,000원" />
        <Stat label="판매 부수" value="128권" />
        <Stat label="출금 가능액" value="6,769원" color={T.ok} />
      </div>
    </div>
