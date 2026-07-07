// app.js — ide-core 화면 조립: 상단 얇은 바 + 챕터 사이드바 + 중앙 에디터(chapter-at-a-time).
// 단일 화면, 패널 추가 없음(dc-2009f043 "스크리브너 단순화" 원칙 계승). packages/doc 의
// mountEditor 를 재사용하되, 챕터 전환은 mountEditor 인스턴스를 destroy 후 재마운트한다
// (mountEditor 에 "다른 html 로 교체" API 가 없다 — 챕터=별개 DOM/에디터 인스턴스).
import { mountEditor } from '../../doc/src/editor.js';
import { nextStatus, moveChapter } from './chapterOrder.js';

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

  /** @type {import('./host.js').ChapterSummary[]} */
  let chapters = [];
  let selectedId = null;
  let ctrl = null; // 현재 mountEditor 컨트롤러
  let dragId = null; // HTML5 DnD 중인 챕터 id

  function setSaveStatus(text) {
    saveStatusEl.textContent = text;
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
    ctrl = mountEditor(editorEl, {
      html: chapter.html,
      onSave: async (html) => {
        const res = await host.saveChapter(id, { html });
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

  await loadAll();

  return {
    destroy() {
      if (ctrl) ctrl.destroy();
    },
  };
}
