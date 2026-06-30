import { chromium } from '@playwright/test';
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1280, height: 900 } });
const errs = [];
p.on('console', m => { if (m.type()==='error') errs.push(m.text()); });
await p.goto('https://potato.hanjul.io/login', { waitUntil: 'networkidle' });
await p.waitForTimeout(800);
await p.screenshot({ path: '/tmp/potato_live_login.png' });
await p.fill('input[type=email]', 'atp2807@gmail.com');
await p.fill('input[type=password]', 'definitely-wrong-pw');
await p.click('button[type=submit]');
await p.waitForTimeout(2500);
const msg = await p.evaluate(() => document.body.innerText);
const shown = msg.includes('올바르지 않') ? '401 처리(와이어 정상)'
  : msg.includes('로그인 실패') ? '로그인 실패(CORS/네트워크 의심)'
  : '메시지 없음';
console.log('LOGIN_RESULT:', shown);
console.log('CONSOLE_ERRORS:', errs.filter(e=>/CORS|blocked|Failed to fetch/i.test(e)).slice(0,3).join(' | ') || 'none');
await b.close();
