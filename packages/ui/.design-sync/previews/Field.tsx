import { Field } from '@hanjul/ui';

export const Input = () => <Field label="이메일" placeholder="me@hanjul.io" />;
export const Textarea = () => (
  <Field label="작가 소개" as="textarea" placeholder="작가 소개를 입력하세요" rows={3} />
);
export const NoLabel = () => <Field placeholder="제목 검색" />;
