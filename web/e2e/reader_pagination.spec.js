import { expect, test } from '@playwright/test';

import { login, seedBook } from './helpers.js';

// 여러 장·다수 문단의 무료 출판본 시드 → 리더에서 2페이지 이상 나온다.
// (무료책=가격0은 소유 없이 전체 열람 → 미리보기 제한을 타지 않는다. price:0은 null이 아니라서
// seedBook의 publish 기본값(price!==null)이 그대로 true가 되어 항상 발행된다.)
function seedLongFreeBook(request, { authorEmail, title }) {
  const para =
    '한줄은 작가가 직접 글을 쓰고 출판하며 판매와 정산까지 스스로 해내는 셀프퍼블리싱 플랫폼입니다. ' +
    '이 문단은 리더 페이지네이션을 확인하기 위해 넉넉히 길게 작성된 본문으로, 여러 줄에 걸쳐 흐르도록 만들어졌습니다.';
  const chapter = (n) => `# ${n}장\n\n` + Array.from({ length: 15 }, () => para).join('\n\n');
  const rawText = [1, 2, 3].map(chapter).join('\n\n');

  return seedBook(request, { authorEmail, title, rawText, price: 0 });
}

// N / M 형태의 현재 페이지 표시 (툴바 우측). 슬래시 양쪽이 숫자인 텍스트는 이것뿐.
const pageIndicator = (page) => page.getByText(/^\d+ \/ \d+$/);

test('리더 페이지 넘기기 + 위치 영속', async ({ page, request }) => {
  const id = await seedLongFreeBook(request, { authorEmail: 'pg-author@x.com', title: '페이지네이션책' });
  await login(page, 'pg-reader@x.com', '페이지독자');

  await page.goto(`/read/${id}`);
  // 첫 페이지 + 다음 페이지가 실제로 존재(2페이지 이상)
  await expect(pageIndicator(page)).toHaveText(/^1 \/ /);

  await page.getByRole('button', { name: '다음' }).click();
  await expect(pageIndicator(page)).toHaveText(/^2 \/ /);

  // 새로고침 후에도 마지막으로 보던 페이지(2)를 이어본다 (localStorage 영속).
  await page.reload();
  await expect(pageIndicator(page)).toHaveText(/^2 \/ /);

  // 이전 버튼으로 1페이지 복귀
  await page.getByRole('button', { name: '이전' }).click();
  await expect(pageIndicator(page)).toHaveText(/^1 \/ /);
});

test('리더 배율(A+) 조절', async ({ page, request }) => {
  const id = await seedLongFreeBook(request, { authorEmail: 'scale-author@x.com', title: '배율책' });
  await login(page, 'scale-reader@x.com', '배율독자');

  await page.goto(`/read/${id}`);
  await expect(page.getByText('배율 1.0x')).toBeVisible();

  // aria-label="글자 크게"가 접근성명 — 시각 텍스트 "A+"를 덮어씀
  await page.getByRole('button', { name: '글자 크게' }).click();
  await expect(page.getByText('배율 1.1x')).toBeVisible();
});
