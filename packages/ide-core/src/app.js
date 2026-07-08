// app.js — ide-core 화면 조립: 상단 얇은 바 + 챕터 사이드바 + 중앙 에디터(chapter-at-a-time).
// 단일 화면, 패널 추가 없음(dc-2009f043 "스크리브너 단순화" 원칙 계승). packages/doc 의
// mountEditor 를 재사용하되, 챕터 전환은 mountEditor 인스턴스를 destroy 후 재마운트한다
// (mountEditor 에 "다른 html 로 교체" API 가 없다 — 챕터=별개 DOM/에디터 인스턴스).
import { mountEditor } from '../../doc/src/editor.js';
import { nextStatus, moveChapter } from './chapterOrder.js';
import { formatSnapshotTimestamp, formatSnapshotLabel } from './snapshotFormat.js';

const STATUS_LABEL = { DRAFT: '초고', REVISING: '퇴고', DONE: '완료' };

/**
 * @param {{host: import('./host.js').HostPort, root: Element}} opts
 * @returns {Promise<{destroy: () => void}>}
 */
export async function mountApp({ host, root }) {
  root.innerHTML = `
    <div id="topbar">
      <span id="book-title"></span>
      <span id="save-status">대기 중</span>
      <span id="auth-status">확인 중…</span>
      <span id="topbar-actions">
        <button type="button" id="login-btn" hidden>로그인</button>
        <button type="button" id="logout-btn" hidden>로그아웃</button>
        <button type="button" id="snapshots-btn">기록</button>
        <button type="button" id="settings-btn">설정</button>
        <button type="button" id="publish-btn">발행</button>
      </span>
    </div>
    <div id="publish-result" hidden></div>
    <div id="snapshots-panel" hidden>
      <div id="snapshots-panel-header">
        <span>스냅샷 기록</span>
        <button type="button" id="take-snapshot-btn">지금 스냅샷</button>
        <button type="button" id="snapshots-close-btn">닫기</button>
      </div>
      <ul id="snapshots-list"></ul>
    </div>
    <div id="shell">
      <aside id="sidebar">
        <ul id="chapter-list"></ul>
        <button type="button" id="new-chapter-btn">+ 새 챕터</button>
        <button type="button" id="import-btn">가져오기</button>
      </aside>
      <main id="editor-pane">
        <div id="editor"></div>
      </main>
    </div>
  `;

  const bookTitleEl = root.querySelector('#book-title');
  const saveStatusEl = root.querySelector('#save-status');
  const listEl = root.querySelector('#chapter-list');
  const newBtn = root.querySelector('#new-chapter-btn');
  const importBtn = root.querySelector('#import-btn');
  const editorEl = root.querySelector('#editor');
  const settingsBtn = root.querySelector('#settings-btn');
  const publishBtn = root.querySelector('#publish-btn');
  const publishResultEl = root.querySelector('#publish-result');
  const authStatusEl = root.querySelector('#auth-status');
  const loginBtn = root.querySelector('#login-btn');
  const logoutBtn = root.querySelector('#logout-btn');
  const snapshotsBtn = root.querySelector('#snapshots-btn');
  const snapshotsPanelEl = root.querySelector('#snapshots-panel');
  const snapshotsListEl = root.querySelector('#snapshots-list');
  const takeSnapshotBtn = root.querySelector('#take-snapshot-btn');
  const snapshotsCloseBtn = root.querySelector('#snapshots-close-btn');

  /** @type {import('./host.js').ChapterSummary[]} */
  let chapters = [];
  let selectedId = null;
  let ctrl = null; // 현재 mountEditor 컨트롤러
  let dragId = null; // HTML5 DnD 중인 챕터 id

  function setSaveStatus(text) {
    saveStatusEl.textContent = text;
  }

  // 로그인 상태 표시(P1 슬라이스5) — me: whoami()/login() 응답({id,email,displayName,role})
  // 또는 로그인 안 됐으면 null. 패널 추가 없이(dc-2009f043) 상단바 한 자리만 토글한다.
  function renderAuthState(me) {
    if (me) {
      authStatusEl.textContent = me.email || me.displayName || '로그인됨';
      loginBtn.hidden = true;
      logoutBtn.hidden = false;
    } else {
      authStatusEl.textContent = '로그인 안 됨';
      loginBtn.hidden = false;
      logoutBtn.hidden = true;
    }
  }

  async function refreshAuthState() {
    try {
      renderAuthState(await host.whoami());
    } catch (err) {
      // 서버 연결 실패 등 — "로그인 안 됨"으로 단정하지 않고 원인을 그대로 보여준다
      // ("로그인 안 됨"과 "서버에 연결할 수 없음"을 사용자가 구분할 수 있게, app.py:whoami 참고).
      authStatusEl.textContent = `로그인 확인 실패: ${err?.message || err}`;
      loginBtn.hidden = false;
      logoutBtn.hidden = true;
    }
  }

  function renderSidebar() {
    listEl.innerHTML = '';
    for (const ch of chapters) {
      const li = document.createElement('li');
      li.className = 'chapter-row' + (ch.id === selectedId ? ' selected' : '');
      li.draggable = true;
      li.dataset.id = String(ch.id);

      const handle = document.createElement('span');
      handle.className = 'chapter-drag-handle';
      handle.textContent = '⠿';
      handle.setAttribute('aria-hidden', 'true');

      const dot = document.createElement('button');
      dot.type = 'button';
      dot.className = `status-dot status-${ch.status}`;
      dot.title = `${STATUS_LABEL[ch.status] || ch.status} (클릭하여 다음 상태로)`;
      dot.addEventListener('click', (e) => {
        e.stopPropagation();
        cycleStatus(ch.id);
      });

      const title = document.createElement('span');
      title.className = 'chapter-title';
      title.textContent = ch.title;

      const synopsis = document.createElement('input');
      synopsis.type = 'text';
      synopsis.className = 'chapter-synopsis';
      synopsis.placeholder = '한줄 시놉시스';
      synopsis.value = ch.synopsis || '';
      synopsis.addEventListener('click', (e) => e.stopPropagation());
      synopsis.addEventListener('change', () => saveSynopsis(ch.id, synopsis.value));

      li.append(handle, dot, title, synopsis);

      li.addEventListener('click', () => selectChapter(ch.id));
      li.addEventListener('dragstart', (e) => {
        dragId = ch.id;
        e.dataTransfer?.setData('text/plain', String(ch.id));
      });
      li.addEventListener('dragover', (e) => e.preventDefault());
      li.addEventListener('drop', (e) => {
        e.preventDefault();
        const dropped = dragId;
        dragId = null;
        if (dropped == null || dropped === ch.id) return;
        reorder(dropped, ch.id);
      });

      listEl.appendChild(li);
    }
  }

  async function loadAll() {
    const book = await host.getBook();
    bookTitleEl.textContent = book.title;
    chapters = await host.listChapters();
    renderSidebar();
    if (chapters.length && selectedId == null) {
      await selectChapter(chapters[0].id);
    }
  }

  async function cycleStatus(id) {
    const ch = chapters.find((c) => c.id === id);
    if (!ch) return;
    ch.status = nextStatus(ch.status);
    renderSidebar();
    await host.saveChapter(id, { status: ch.status });
  }

  async function saveSynopsis(id, synopsis) {
    const ch = chapters.find((c) => c.id === id);
    if (ch) ch.synopsis = synopsis;
    await host.saveChapter(id, { synopsis });
  }

  async function reorder(draggedId, targetId) {
    const ids = chapters.map((c) => c.id);
    const nextIds = moveChapter(ids, draggedId, targetId);
    chapters = nextIds.map((id) => chapters.find((c) => c.id === id));
    renderSidebar();
    await host.reorderChapters(nextIds);
  }

  // selectChapter()와 스냅샷 복원(restoreSnapshot 이후) 양쪽이 "챕터 id + html 로
  // mountEditor 를 새로 붙인다"는 동일 작업을 하므로 공통 헬퍼로 뺐다(설계결정 5
  // "복원 시 에디터 내용 갱신").
  function mountEditorForChapter(chapterId, html) {
    return mountEditor(editorEl, {
      html,
      onSave: async (saveHtml) => {
        const res = await host.saveChapter(chapterId, { html: saveHtml });
        setSaveStatus(`저장됨 · ${res.savedAt}`);
        return res;
      },
      onDirty: (dirty) => {
        if (dirty) setSaveStatus('편집 중… (자동저장 대기 2초)');
      },
      onStatus: (state, err) => {
        if (state === 'saving') setSaveStatus('저장 중…');
        if (state === 'error') setSaveStatus(`저장 실패: ${err?.message || err}`);
      },
    });
  }

  async function selectChapter(id) {
    if (id === selectedId) return;
    // 챕터 전환 시 dirty 면 자동 save 후 전환(desc: "선택 챕터 chapter-at-a-time").
    if (ctrl && ctrl.isDirty()) {
      await ctrl.save();
    }
    if (ctrl) {
      ctrl.destroy();
      ctrl = null;
    }
    const chapter = await host.loadChapter(id);
    selectedId = id;
    renderSidebar();
    ctrl = mountEditorForChapter(id, chapter.html);
  }

  // 스냅샷 패널(P1 슬라이스6) — 상단바 [기록] 버튼 하나로 토글. 패널 이외 레이아웃은
  // 건드리지 않는다(설계결정 5). html 은 목록에 없어(HOST_PORT.md listSnapshots) 가벼움.
  async function renderSnapshotsList() {
    if (selectedId == null) {
      snapshotsListEl.innerHTML = '';
      return;
    }
    const snapshots = await host.listSnapshots(selectedId);
    snapshotsListEl.innerHTML = '';
    for (const snap of snapshots) {
      const li = document.createElement('li');
      li.className = 'snapshot-row';

      const meta = document.createElement('span');
      meta.className = 'snapshot-meta';
      meta.textContent =
        `${formatSnapshotTimestamp(snap.createdAt)} · ${formatSnapshotLabel(snap.label)} · ${snap.chars}자`;

      const restoreBtn = document.createElement('button');
      restoreBtn.type = 'button';
      restoreBtn.textContent = '복원';
      restoreBtn.addEventListener('click', () => restoreSnapshot(snap.id));

      li.append(meta, restoreBtn);
      snapshotsListEl.appendChild(li);
    }
  }

  async function restoreSnapshot(snapshotId) {
    const restored = await host.restoreSnapshot(snapshotId);
    // 복원된 챕터로 에디터 내용을 즉시 갱신(설계결정 4 "복원된 챕터 반환 → 에디터 리로드용").
    if (ctrl) {
      ctrl.destroy();
      ctrl = null;
    }
    ctrl = mountEditorForChapter(selectedId, restored.html);
    setSaveStatus('스냅샷 복원됨');
    await renderSnapshotsList(); // 복원 직전 자동 스냅샷("복원 전 자동")이 새로 추가됐으니 목록도 갱신
  }

  snapshotsBtn.addEventListener('click', async () => {
    const opening = snapshotsPanelEl.hidden;
    snapshotsPanelEl.hidden = !opening;
    if (opening) await renderSnapshotsList();
  });

  snapshotsCloseBtn.addEventListener('click', () => {
    snapshotsPanelEl.hidden = true;
  });

  takeSnapshotBtn.addEventListener('click', async () => {
    const label = window.prompt('스냅샷 라벨(선택, 비워두면 자동 저장으로 표시)', '');
    await host.takeSnapshot(selectedId, label || undefined);
    await renderSnapshotsList();
  });

  newBtn.addEventListener('click', async () => {
    const title = window.prompt('새 챕터 제목', '');
    if (!title) return;
    const { id } = await host.createChapter({ title });
    await loadAll();
    await selectChapter(id);
  });

  // 원고 가져오기(P1 슬라이스3) — 파일 선택은 호스트(파이썬 다이얼로그) 몫, 여기선
  // 진행중 표시 → 완료 후 목록 갱신 → 새로 들어온 첫 챕터로 전환만 담당한다.
  importBtn.addEventListener('click', async () => {
    importBtn.disabled = true;
    const originalLabel = importBtn.textContent;
    importBtn.textContent = '가져오는 중…';
    try {
      const result = await host.importFile();
      if (result.cancelled) return;
      await loadAll(); // chapters 갱신 + 사이드바 재렌더(선택은 아래에서 새 챕터로 전환)
      if (result.chapterIds?.length) {
        await selectChapter(result.chapterIds[0]);
      }
    } catch (err) {
      setSaveStatus(`가져오기 실패: ${err?.message || err}`);
    } finally {
      importBtn.disabled = false;
      importBtn.textContent = originalLabel;
    }
  });

  // 로그인/로그아웃(P1 슬라이스5) — 클릭 시 시스템 브라우저가 열린다(host.login() 내부에서
  // 루프백 리스너 오픈 → 브라우저 오픈 → 콜백 대기까지 블로킹). 완료/실패 전까지 버튼을
  // 잠가 중복 클릭을 막는다.
  loginBtn.addEventListener('click', async () => {
    loginBtn.disabled = true;
    const originalLabel = loginBtn.textContent;
    loginBtn.textContent = '로그인 중… (브라우저 확인)';
    try {
      const me = await host.login();
      renderAuthState(me);
    } catch (err) {
      setSaveStatus(`로그인 실패: ${err?.message || err}`);
    } finally {
      loginBtn.disabled = false;
      loginBtn.textContent = originalLabel;
    }
  });

  logoutBtn.addEventListener('click', async () => {
    await host.logout();
    renderAuthState(null);
  });

  // 발행 설정(P1 슬라이스4) — apiBase/token 수동 입력(prompt 관례, 이 슬라이스는
  // OAuth 없음 — 다음 슬라이스에서 대체). getSettings() 의 token 은 마스킹된 값이라
  // "새 값"으로 그대로 되돌려 넣지 않는다 — 비워두면 기존 값 유지.
  settingsBtn.addEventListener('click', async () => {
    const current = await host.getSettings();
    window.alert(
      current.apiBase || current.hasToken
        ? `현재 apiBase: ${current.apiBase || '(없음)'} / 토큰: ${current.hasToken ? current.token : '(없음)'}`
        : '아직 설정된 발행 서버가 없어요.'
    );

    const apiBase = window.prompt(
      '발행 서버 주소 (apiBase, 예: http://127.0.0.1:28000) — 비워두면 유지',
      current.apiBase || 'http://127.0.0.1:28000'
    );
    const token = window.prompt('로그인 토큰 (Bearer) — 비워두면 유지', '');

    const patch = {};
    if (apiBase) patch.apiBase = apiBase;
    if (token) patch.token = token;
    if (Object.keys(patch).length === 0) return;

    await host.saveSettings(patch);
    setSaveStatus('발행 설정 저장됨');
  });

  // 발행 결과/프리플라이트 위반 표시 — 패널 추가 없이(dc-2009f043) 상단바 바로 아래
  // 한 줄짜리 배너 영역을 성공/실패 내용으로 채웠다 비웠다만 한다.
  function renderPublishResult(result) {
    publishResultEl.hidden = false;
    publishResultEl.innerHTML = '';

    const closeBtn = document.createElement('button');
    closeBtn.type = 'button';
    closeBtn.className = 'publish-result-close';
    closeBtn.textContent = '닫기';
    closeBtn.addEventListener('click', () => {
      publishResultEl.hidden = true;
    });

    if (result.ok) {
      const msg = document.createElement('p');
      msg.textContent = `발행 완료 — 챕터 ${result.chapterCount}개 (책 ID: ${result.remoteBookId})`;
      publishResultEl.append(msg, closeBtn);
      return;
    }

    if (result.violations?.length) {
      const msg = document.createElement('p');
      msg.textContent =
        `발행 중단 — 서버가 지원하지 않는 서식이 ${result.violations.length}곳 있어요 ` +
        '(표/이미지/목록/코드 블록, 밑줄·링크 등은 아직 지원하지 않아요):';
      const list = document.createElement('ul');
      for (const v of result.violations) {
        const li = document.createElement('li');
        li.textContent = `${v.chapterTitle ?? '(제목 없음)'} — ${v.blockType}: ${v.reason}`;
        list.appendChild(li);
      }
      publishResultEl.append(msg, list, closeBtn);
      return;
    }

    const msg = document.createElement('p');
    if (result.error?.status === 401) {
      // 401 시 로그인 유도(P1 슬라이스5) — 토큰 만료/무효일 수 있으니 상단 로그인 상태도
      // "로그인 안 됨"으로 즉시 반영(다음 whoami() 호출을 기다리지 않고).
      msg.textContent = '로그인이 필요해요 — 상단바에서 로그인해주세요.';
      renderAuthState(null);
    } else {
      msg.textContent = `발행 실패 — ${result.error?.message || '알 수 없는 오류'}`;
    }
    publishResultEl.append(msg, closeBtn);
  }

  publishBtn.addEventListener('click', async () => {
    publishBtn.disabled = true;
    const originalLabel = publishBtn.textContent;
    publishBtn.textContent = '발행 중…';
    try {
      const result = await host.publish();
      renderPublishResult(result);
    } catch (err) {
      renderPublishResult({ ok: false, error: { message: err?.message || String(err) } });
    } finally {
      publishBtn.disabled = false;
      publishBtn.textContent = originalLabel;
    }
  });

  await loadAll();
  await refreshAuthState();

  return {
    destroy() {
      if (ctrl) ctrl.destroy();
    },
  };
}
