// main.js — ide-core 진입점. Host Port v0(pywebview 어댑터)로 화면을 마운트한다.
// 스모크 테스트(desktop/app.py --smoke)가 evaluate_js 로 확인할 때 쓰는 훅으로
// window.__editorCtrl 대신 window.__ideApp(mountApp 반환값)을 심어둔다.
import { createHost } from './host.js';
import { mountApp } from './app.js';
import { applyThemeTokens } from './theme.js';
import '../../doc/src/doc.css';
import './style.css';

// @hanjul/ui 토큰 → --hj-* CSS 변수. style.css 가 이 변수들을 참조하므로 마운트 전에 적용.
applyThemeTokens();

const host = createHost({ kind: 'pywebview' });
const root = document.getElementById('app');

mountApp({ host, root })
  .then((app) => {
    window.__ideApp = app;
  })
  .catch((err) => {
    // 마운트 자체가 실패하면(호스트 브리지 미준비 등) 사용자가 보이는 자리에 원인을 남긴다.
    root.textContent = `한줄 IDE 로드 실패: ${err?.message || err}`;
    console.error(err);
  });
