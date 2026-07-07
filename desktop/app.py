"""한줄 IDE P1 — Host Port v0 데스크탑 구현.

packages/ide-core(웹뷰 앱)에 desktop/store.py(SQLite) 위에서 동작하는 Host Port
계약(packages/ide-core/HOST_PORT.md)을 pywebview js_api 로 제공한다. P0 스파이크
(desktop/webapp)는 packages/ide-core 로 대체됐다.

실행:
    cd desktop && .venv/bin/python app.py            # GUI 창
    cd desktop && .venv/bin/python app.py --smoke     # 자동 스모크(수 초 내 종료)

빌드 산출물 준비(최초 1회 또는 packages/ide-core/src 변경 후):
    npm install                       # 저장소 루트 — workspaces 등록
    npm run build -w packages/ide-core   # dist/index.html 생성 — 이 앱이 그걸 로드한다
"""

import argparse
import json
import sys
import time
from pathlib import Path

import webview

from store import Store

BASE_DIR = Path(__file__).resolve().parent
DIST_INDEX = BASE_DIR.parent / "packages" / "ide-core" / "dist" / "index.html"


class Api:
    """js_api 로 노출되는 Host Port v0. 메서드명은 Python 관례상 snake_case —
    packages/ide-core/src/host.js 의 pywebview 어댑터가 camelCase 계약으로 감싼다.
    각 메서드는 그대로 store.py 에 위임(로직은 store 가 정본)."""

    def __init__(self, store):
        self._store = store

    def get_book(self):
        return self._store.get_book()

    def list_chapters(self):
        return self._store.list_chapters()

    def load_chapter(self, chapter_id):
        return self._store.load_chapter(chapter_id)

    def save_chapter(self, chapter_id, patch):
        return self._store.save_chapter(chapter_id, patch)

    def create_chapter(self, title):
        return self._store.create_chapter(title)

    def delete_chapter(self, chapter_id):
        return self._store.delete_chapter(chapter_id)

    def reorder_chapters(self, ids):
        return self._store.reorder_chapters(ids)


def run_smoke(window, timeout_s=5.0, poll_interval_s=0.1):
    """창 로드 완료 후 확인 순서:
      1) 마운트 — [contenteditable] 존재.
      2) 브리지 CRUD 왕복 — createChapter → saveChapter(html) → reorderChapters →
         (프로세스 재시작 없이) listChapters 로 순서, loadChapter 로 내용을 재확인.

    주의(lr-9a45e6e4): pywebview evaluate_js 는 콜백 없이 쓰면 Promise 를 즉시
    JSON.stringify 해 "{}" 를 반환한다(별도 스레드에서 실제 처리가 끝나기 전에 값을
    읽어버리는 레이스). 그래서 JS 쪽에 완료 플래그(window.__smokeDone/__smokeResult)를
    심어두고 그 플래그가 설 때까지 폴링한다 — app.py:39-105(P0 스파이크)에서 이미
    검증된 패턴을 그대로 계승.
    """
    results = {}
    try:
        # 0) 앱 마운트 대기 — main.js 는 mountApp() 이 getBook/listChapters/
        #    loadChapter 를 비동기 브리지로 먼저 fetch 한 뒤에야 에디터를 마운트하고
        #    window.__ideApp 을 심는다. 'loaded' 이벤트 시점엔 아직 안 끝났을 수 있어
        #    (실측: contenteditable_present가 false로 나온 적 있음) 브리지 폴링과
        #    동일한 이유로 여기도 폴링한다.
        deadline = time.monotonic() + timeout_s
        app_mounted = False
        while time.monotonic() < deadline:
            app_mounted = bool(window.evaluate_js("window.__ideApp !== undefined"))
            if app_mounted:
                break
            time.sleep(poll_interval_s)
        results["app_mounted_within_timeout"] = app_mounted

        has_editor = window.evaluate_js(
            'document.querySelector("[contenteditable]") !== null'
        )
        results["contenteditable_present"] = bool(has_editor)

        # 브리지 CRUD 왕복 — 실제 완료/결과는 JS 쪽 전역 플래그에 남긴다(폴링 대상).
        window.evaluate_js(
            """
            window.__smokeDone = false;
            (async function () {
              try {
                const before = await window.pywebview.api.list_chapters();
                const created = await window.pywebview.api.create_chapter('스모크 챕터');
                const saved = await window.pywebview.api.save_chapter(
                  created.id,
                  { html: '<article data-juldoc="1"><p>스모크 본문</p></article>' }
                );
                const afterCreate = await window.pywebview.api.list_chapters();
                const idsAfterCreate = afterCreate.map((c) => c.id);
                // 새로 만든 챕터를 맨 앞으로 재배열 — 재시작 없이 순서 재확인 대상.
                const reordered = [created.id, ...idsAfterCreate.filter((id) => id !== created.id)];
                await window.pywebview.api.reorder_chapters(reordered);
                const afterReorder = await window.pywebview.api.list_chapters();
                const loaded = await window.pywebview.api.load_chapter(created.id);
                window.__smokeResult = {
                  chaptersBeforeCreate: before.length,
                  chaptersAfterCreate: afterCreate.length,
                  createdId: created.id,
                  savedAt: saved.savedAt,
                  orderIdsAfterReorder: afterReorder.map((c) => c.id),
                  firstIdMatchesCreated: afterReorder.length > 0 && afterReorder[0].id === created.id,
                  loadedStatus: loaded.status,
                  loadedHtmlMatches: loaded.html.includes('스모크 본문'),
                };
              } catch (e) {
                window.__smokeError = String(e && e.message ? e.message : e);
              } finally {
                window.__smokeDone = true;
              }
            })();
            """
        )

        deadline = time.monotonic() + timeout_s
        done = False
        while time.monotonic() < deadline:
            done = bool(window.evaluate_js("window.__smokeDone === true"))
            if done:
                break
            time.sleep(poll_interval_s)
        results["bridge_calls_done_within_timeout"] = done

        smoke_result = window.evaluate_js("window.__smokeResult")
        smoke_error = window.evaluate_js("window.__smokeError")
        results["smoke_result"] = smoke_result
        results["smoke_error"] = smoke_error

        results["ok"] = bool(
            app_mounted
            and results.get("contenteditable_present")
            and done
            and smoke_result
            and not smoke_error
            and smoke_result.get("chaptersAfterCreate") == smoke_result.get("chaptersBeforeCreate", -1) + 1
            and smoke_result.get("firstIdMatchesCreated")
            and smoke_result.get("loadedStatus") == "DRAFT"
            and smoke_result.get("loadedHtmlMatches")
        )
    except Exception as exc:  # 스모크 자체가 실패한 원인을 있는 그대로 남긴다.
        results["error"] = repr(exc)
        results["ok"] = False

    print("SMOKE_RESULT " + json.dumps(results, ensure_ascii=False))
    sys.stdout.flush()
    window.destroy()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="창을 띄운 뒤 자동으로 마운트/Host Port CRUD 왕복을 확인하고 종료",
    )
    parser.add_argument(
        "--db",
        default=None,
        help="대체 SQLite 파일 경로(검증/반복 실행용). 기본은 desktop/data/ide.db.",
    )
    args = parser.parse_args()

    if not DIST_INDEX.exists():
        print(
            f"빌드 산출물 없음: {DIST_INDEX}\n"
            "먼저 저장소 루트에서 `npm install && npm run build -w packages/ide-core` 를 실행하세요.",
            file=sys.stderr,
        )
        sys.exit(1)

    store = Store(args.db) if args.db else Store()
    api = Api(store)
    window = webview.create_window(
        "한줄 IDE",
        str(DIST_INDEX),
        js_api=api,
        width=1200,
        height=800,
        # 스모크는 숨김 창으로 — 사용자 데스크탑에 창 깜빡임 금지 (lr-9a45e6e4 후속)
        hidden=args.smoke,
    )

    if args.smoke:
        window.events.loaded += lambda: run_smoke(window)

    webview.start()


if __name__ == "__main__":
    main()
