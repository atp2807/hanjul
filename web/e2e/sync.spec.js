import { expect, test } from '@playwright/test';

// 코어 서버 동기화: 두 브라우저(기기)가 같은 책을 열면 CRDT로 수렴.
test('두 기기 실시간 동기화', async ({ browser }) => {
  const room = 'sync-room-realtime';
  const a = await browser.newContext();
  const b = await browser.newContext();
  const pa = await a.newPage();
  const pb = await b.newPage();
  await pa.goto(`/write/${room}`);
  await pb.goto(`/write/${room}`);

  await pa.locator('.ProseMirror').click();
  await pa.keyboard.type('실시간 동기화 문장');

  // B 기기에 별도 입력 없이 나타남
  await expect(pb.locator('.ProseMirror')).toContainText('실시간 동기화 문장', { timeout: 10000 });

  await a.close();
  await b.close();
});

test('오프라인 입력 → 재연결 시 충돌 없이 수렴', async ({ browser }) => {
  const room = 'sync-room-offline';
  const a = await browser.newContext();
  const b = await browser.newContext();
  const pa = await a.newPage();
  const pb = await b.newPage();
  await pa.goto(`/write/${room}`);
  await pb.goto(`/write/${room}`);

  await pa.locator('.ProseMirror').click();
  await pa.keyboard.type('온라인 먼저');
  await expect(pb.locator('.ProseMirror')).toContainText('온라인 먼저', { timeout: 10000 });

  // A 오프라인 → 입력 → 재연결
  await a.setOffline(true);
  await pa.keyboard.type(' 그리고 오프라인 추가');
  await a.setOffline(false);

  // 수렴: 오프라인 추가분 도착 + 기존 내용 보존(분기/리셋 아님)
  await expect(pb.locator('.ProseMirror')).toContainText('오프라인 추가', { timeout: 15000 });
  await expect(pb.locator('.ProseMirror')).toContainText('온라인 먼저');

  await a.close();
  await b.close();
});
