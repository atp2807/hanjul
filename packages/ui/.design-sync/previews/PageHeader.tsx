import { Button, PageHeader } from '@hanjul/ui';

export const Basic = () => (
  <PageHeader title="정산·출금" subtitle="판매 정산금을 등록한 계좌로 출금 신청하세요." />
);

export const WithAction = () => (
  <PageHeader
    title="내 서재"
    subtitle="구매한 책"
    right={<Button size="sm">전체 보기</Button>}
  />
);
