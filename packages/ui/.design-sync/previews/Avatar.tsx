import { Avatar } from '@hanjul/ui';

export const Initials = () => <Avatar name="김운영" size="lg" />;
export const SizeXs = () => <Avatar name="이민서" size="xs" />;
export const SizeXl = () => <Avatar name="박정산" size="xl" />;
export const Latin = () => <Avatar name="Somin Yoo" size="lg" />;
export const Online = () => <Avatar name="정해린" size="lg" status="online" />;
export const Busy = () => <Avatar name="서가의밤" size="lg" status="busy" />;
export const Ring = () => <Avatar name="윤가람" size="lg" ring />;
export const Image = () => (
  <Avatar name="정해린" size="lg" src="https://i.pravatar.cc/120?img=5" status="online" ring />
);
