"""한줄 IDE P1 — Host Port v0 데스크탑 구현.

packages/ide-core(웹뷰 앱)에 desktop/store.py(SQLite) 위에서 동작하는 Host Port
계약(packages/ide-core/HOST_PORT.md)을 pywebview js_api 로 제공한다. P0 스파이크
(desktop/webapp)는 packages/ide-core 로 대체됐다.

실행:
    cd desktop && .venv/bin/python app.py            # GUI 창
    cd desktop && .venv/bin/python app.py --smoke     # 자동 스모크(수 초 내 종료)
    cd desktop && .venv/bin/python app.py --perf      # L0 성능 계측 하네스(dc-81277381, 숨김창)

빌드 산출물 준비(최초 1회 또는 packages/ide-core/src 변경 후):
    npm install                       # 저장소 루트 — workspaces 등록
    npm run build -w packages/ide-core   # dist/index.html + dist/perf.html 생성 — 이 앱이 그걸 로드한다
"""

import argparse
import json
import sys
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import webview

from auth_flow import run_login_flow
from backup import backup_now as push_backup  # P1 슬라이스7 — backup.py:38
from importer import import_manuscript
# _request 재사용 — publisher.py:179 (stdlib urllib 기반 HTTP 헬퍼, 새 의존성 없이 재사용)
from publisher import PublishHttpError, _request
from publisher import publish as publish_book
from store import Store
from store import _default_data_dir  # PERF_REPORT_PATH 도 store.py 와 동일한 사용자 데이터 디렉터리 관례
from store import _now_iso as _local_now_iso  # 백업시각도 store.py 와 동일 포맷/시계 사용
from store import _parse_ts as _local_parse_ts  # 위와 동일 포맷으로 되읽기(스로틀 경과시간 계산)
from token_store import KeyringUnavailableError, delete_token, get_token, set_token

BASE_DIR = Path(__file__).resolve().parent
# 소스 실행(BASE_DIR=desktop/)에서는 저장소 루트가 BASE_DIR.parent. PyInstaller 번들
# (``sys.frozen``)에서는 ``packages/ide-core/dist``를 hanjul_ide.spec 의 datas 로
# 번들 루트(``sys._MEIPASS`` — onedir 는 실행파일과 같은 폴더)에 그대로 심어두므로
# ASSETS_ROOT = 번들 루트 자체를 써야 한다(BASE_DIR.parent 는 번들 밖이라 존재하지 않음).
ASSETS_ROOT = Path(sys._MEIPASS) if getattr(sys, "frozen", False) else BASE_DIR.parent
DIST_INDEX = ASSETS_ROOT / "packages" / "ide-core" / "dist" / "index.html"
# --perf 전용 산출물(packages/ide-core/perf.html 진입점) — L0 계측 하네스(dc-81277381).
# 챕터/호스트 브리지가 없는 별개 페이지라 Store/js_api 를 전혀 쓰지 않는다.
PERF_INDEX = ASSETS_ROOT / "packages" / "ide-core" / "dist" / "perf.html"
# report.json 은 번들 내부(쓰기 불확실/재설치 시 소실)가 아니라 store.py 와 동일한 사용자
# 데이터 디렉터리 관례를 따른다(개발 실행은 지금까지처럼 desktop/perf/report.json 그대로).
PERF_REPORT_PATH = (
    (_default_data_dir() / "perf" / "report.json")
    if getattr(sys, "frozen", False)
    else BASE_DIR / "perf" / "report.json"
)

# 발행 설정 화면(app.js settingsBtn 핸들러)이 쓰는 기본값과 동일 — 로그인 시에도 apiBase가
# 아직 없으면(최초 실행) 같은 기본으로 폴백한다.
_DEFAULT_API_BASE = "http://127.0.0.1:28000"

# 자동 백업(P1 슬라이스7) 최소 간격 — saveChapter 처리 후 마지막 백업이 이보다 오래됐을 때만
# (또는 아예 없을 때) 백그라운드로 자동 백업을 시도한다. store.py 스냅샷의
# SNAPSHOT_AUTO_INTERVAL_S(10분)보다 여유를 둬 서버 부하를 낮춘다 — 로컬 스냅샷은 "글이 안
# 날아간다" 안전망이라 더 촘촘해야 하고, 서버 백업은 네트워크 왕복이 있는 이차 안전망이다.
_AUTO_BACKUP_INTERVAL_S = 900  # 15분

# pywebview create_file_dialog 의 file_types 포맷: "설명 (*.ext[;*.ext...])"
# (실측: desktop/.venv/lib/python3.14/site-packages/webview/window.py:534-535 docstring).
_IMPORT_FILE_TYPES = (
    "지원 문서 (*.txt;*.md;*.docx;*.hwp;*.hwpx)",
    "모든 파일 (*.*)",
)


def _mask_token(token):
    """설정 조회 응답에 원본 토큰을 그대로 싣지 않기 위한 마스킹 — 끝 4자만 남긴다.
    (get_settings() 는 "지금 뭐가 설정돼 있나" 확인용이지 값을 그대로 복사해가는 용도가
    아니다 — 새 값은 항상 save_settings() 로 새로 입력받는다.)"""
    if not token:
        return None
    if len(token) <= 4:
        return "*" * len(token)
    return "*" * (len(token) - 4) + token[-4:]


def _effective_token(raw_settings):
    """실제 발행/조회에 쓸 토큰 — keyring(P1 슬라이스5 실 로그인의 정본 저장소) 우선,
    없으면(로그인 안 했거나 keyring 백엔드 자체가 없는 환경) setting 테이블의 평문
    폴백(dev 수동 입력, 여전히 save_settings({token: ...})로 동작). keyring 조회 자체가
    실패해도(백엔드 없음) 여기서는 조용히 평문으로 내려간다 — "keyring이 없으면 명확한
    에러"는 login()/logout()처럼 keyring에 새로 쓰려는 시도에만 적용된다(설계결정 4)."""
    try:
        token = get_token()
    except KeyringUnavailableError:
        token = None
    return token or raw_settings.get("token")


class Api:
    """js_api 로 노출되는 Host Port v0. 메서드명은 Python 관례상 snake_case —
    packages/ide-core/src/host.js 의 pywebview 어댑터가 camelCase 계약으로 감싼다.
    각 메서드는 그대로 store.py 에 위임(로직은 store 가 정본)."""

    def __init__(self, store):
        self._store = store
        self._window = None  # main() 이 create_window 직후 채운다(파일 다이얼로그용).
        # 자동 백업(P1 슬라이스7) 중복 발사 방지 — 프로세스 메모리로 충분(재시작하면 리셋돼도
        # 무해, 어차피 last_backup_at 스로틀이 다시 걸린다).
        self._auto_backup_lock = threading.Lock()
        self._auto_backup_in_flight = False

    def get_book(self):
        return self._store.get_book()

    def list_chapters(self):
        return self._store.list_chapters()

    def load_chapter(self, chapter_id):
        return self._store.load_chapter(chapter_id)

    def save_chapter(self, chapter_id, patch):
        """저장 자체는 항상 로컬 우선 — 반환 직전 자동 백업 조건을 확인해 필요하면 백그라운드
        스레드로 push 를 "발사하고 잊는다"(fire-and-forget). 스레드 시작 자체가 실패해도
        (극히 드묾) save_chapter 결과에는 영향 없다 — 저장은 이미 끝난 뒤다."""
        result = self._store.save_chapter(chapter_id, patch)
        try:
            self._maybe_auto_backup()
        except Exception:
            pass  # 자동 백업 트리거 판단조차 저장을 막아선 안 된다(설계결정 3, 로컬우선).
        return result

    def create_chapter(self, title):
        return self._store.create_chapter(title)

    def delete_chapter(self, chapter_id):
        return self._store.delete_chapter(chapter_id)

    def reorder_chapters(self, ids):
        return self._store.reorder_chapters(ids)

    def list_snapshots(self, chapter_id):
        return self._store.list_snapshots(chapter_id)

    def take_snapshot(self, chapter_id, label=None):
        return self._store.take_snapshot(chapter_id, label)

    def restore_snapshot(self, snapshot_id):
        return self._store.restore_snapshot(snapshot_id)

    def import_file(self, path=None):
        """원고 가져오기(P1 슬라이스3). path 가 없으면 OPEN 파일 다이얼로그를 띄운다
        (스모크/테스트는 path 를 직접 넘겨 다이얼로그를 건너뛴다). 다이얼로그 취소 시
        ``{"cancelled": True}``. 성공 시 ``{"importedCount", "chapterIds"}``."""
        if path is None:
            if self._window is None:
                raise RuntimeError("import_file: 창이 아직 준비되지 않음")
            selected = self._window.create_file_dialog(
                webview.FileDialog.OPEN,
                allow_multiple=False,
                file_types=_IMPORT_FILE_TYPES,
            )
            if not selected:
                return {"cancelled": True}
            path = selected[0]

        chapters = import_manuscript(path)
        book_id = self._store.get_book()["id"]
        result = self._store.import_chapters(book_id, chapters)
        return {"importedCount": len(chapters), "chapterIds": result["chapterIds"]}

    def get_settings(self):
        """발행 설정 조회(P1 슬라이스4) — token 은 keyring 우선 · 평문 폴백(``_effective_token``,
        P1 슬라이스5) 결과를 응답에서 마스킹(끝 4자만 노출). ``hasToken`` 으로 저장 여부를
        구분(마스킹된 문자열만 보고는 알기 애매해서)."""
        raw = self._store.get_settings()
        token = _effective_token(raw)
        return {
            "apiBase": raw.get("apiBase"),
            "token": _mask_token(token),
            "hasToken": bool(token),
        }

    def save_settings(self, settings):
        """발행 설정 저장(P1 슬라이스4, dev 수동 입력 폴백) — patch 에 담긴 필드(apiBase/token)만
        갱신. 실 로그인(login())은 이 경로를 안 쓰고 keyring에 직접 쓴다 — 여기 저장한 token은
        keyring이 비어있을 때만 ``_effective_token`` 에 의해 쓰인다."""
        return self._store.save_settings(settings or {})

    def publish(self):
        """로컬 책 전체를 서버로 발행(P1 슬라이스4) — keyring 우선 · 평문 폴백 토큰을 쓴다
        (P1 슬라이스5). 반환 형태는 desktop/publisher.py:publish() 그대로
        (``{"ok": True, "remoteBookId", "chapterCount"}`` /
        ``{"ok": False, "violations": [...]}`` / ``{"ok": False, "error": {...}}``)."""
        raw = self._store.get_settings()
        effective_settings = {**raw, "token": _effective_token(raw)}
        return publish_book(self._store, effective_settings)

    # ── 백업 push(P1 슬라이스7) ──────────────────────────────────────────

    def _effective_publish_settings(self):
        """publish()/backup_now() 공용 — keyring 우선·평문 폴백 토큰을 채운 설정 dict."""
        raw = self._store.get_settings()
        return {**raw, "token": _effective_token(raw)}

    def backup_now(self):
        """수동 백업("백업" 버튼) — 결과에 ``backedUpAt``(로컬 ISO 시각)을 얹어 반환한다.
        실패(연결 실패·4xx/5xx·미로그인 등)는 예외를 그대로 올린다 — 자동 백업과 달리
        사용자가 명시적으로 누른 동작이라 조용히 삼키지 않는다(ide-core 가 실패를 표시)."""
        settings = self._effective_publish_settings()
        result = push_backup(self._store, settings)
        backed_up_at = _local_now_iso()
        self._store.set_last_backup_at(backed_up_at)
        return {**result, "backedUpAt": backed_up_at}

    def get_backup_status(self):
        """상단바 "마지막 백업 시각" 표시용 — 네트워크 호출 없이 로컬에 저장된 마지막 성공
        시각만 읽는다(백업한 적 없으면 None)."""
        return {"lastBackupAt": self._store.get_last_backup_at()}

    def _maybe_auto_backup(self):
        """saveChapter 성공 직후 호출 — 토큰이 있고 마지막 "성공한" 백업이 15분보다
        오래됐으면(또는 아예 없으면) 백그라운드 스레드로 best-effort 백업을 발사한다.

        `last_backup_at`은 성공한 백업만 기록한다(상단바 표시가 거짓으로 "방금 백업됨"을
        보여주지 않도록) — 대신 짧은 간격의 중복 발사는 인스턴스 플래그
        `_auto_backup_in_flight`(락으로 보호, DB 아닌 메모리 — 프로세스 생존 기간만
        유효하면 충분)로 막는다. 트레이드오프: 네트워크가 계속 끊겨 있으면 saveChapter 마다
        재시도 스레드가 뜬다(15분 대기 없이) — best-effort·데몬 스레드라 무해하고, 오히려
        연결이 곧 복구됐을 때 15분을 기다리지 않고 바로 이어지는 편이 낫다고 판단했다.
        """
        settings = self._effective_publish_settings()
        token = settings.get("token")
        if not token:
            return
        last = self._store.get_last_backup_at()
        if last is not None:
            elapsed = (datetime.now() - _local_parse_ts(last)).total_seconds()
            if elapsed < _AUTO_BACKUP_INTERVAL_S:
                return
        with self._auto_backup_lock:
            if self._auto_backup_in_flight:
                return  # 이미 백그라운드 백업 진행 중 — 중복 스레드 방지
            self._auto_backup_in_flight = True
        threading.Thread(target=self._run_background_backup, args=(settings,), daemon=True).start()

    def _run_background_backup(self, settings):
        """백그라운드 스레드 본체 — 실패해도 절대 앱에 드러나지 않는다(로컬우선 원칙,
        설계결정 3). 성공했을 때만 last_backup_at 을 갱신한다."""
        try:
            push_backup(self._store, settings)
            self._store.set_last_backup_at(_local_now_iso())
        except Exception:
            pass  # best-effort — 실패를 삼킨다(타이핑·저장은 이미 끝난 뒤라 영향 없음)
        finally:
            with self._auto_backup_lock:
                self._auto_backup_in_flight = False

    def login(self):
        """실 로그인(P1 슬라이스5) — 시스템 브라우저 Google OAuth + 루프백 콜백 + 키체인 저장.

        지금까지의 "설정 화면에 토큰 수동 붙여넣기"를 대체한다(수동 입력은 save_settings()로
        여전히 폴백 가능). apiBase 는 저장된 설정을 쓰고 없으면 ``_DEFAULT_API_BASE`` 로
        폴백(설정 화면 기본값과 동일). 성공 시 whoami() 와 동일한 형태를 반환한다.

        keyring 저장 실패(``KeyringUnavailableError``)·타임아웃(``LoginTimeoutError``)·
        콜백 에러(``LoginCallbackError``)는 조용히 삼키지 않고 그대로 올린다 — 호출자
        (packages/ide-core/src/app.js)가 실패로 받아 사용자에게 보여준다."""
        raw = self._store.get_settings()
        api_base = raw.get("apiBase") or _DEFAULT_API_BASE

        def build_authorization_url(redirect_uri):
            next_qs = quote(redirect_uri, safe="")
            _, body = _request({"apiBase": api_base}, "GET", f"/auth/google/login?next={next_qs}")
            return body["authorizationUrl"]

        result = run_login_flow(build_authorization_url, timeout_s=120)
        set_token(result["token"])  # KeyringUnavailableError 는 여기서 그대로 전파(설계결정 4)
        return self.whoami()

    def logout(self):
        """keyring 토큰 삭제(멱등) — 평문 setting.token(dev 수동 입력)은 별개 폴백이라 안 건드린다."""
        delete_token()
        return {"ok": True}

    def whoami(self):
        """현재 로그인 계정(``GET /api/me``, backend/src/features/accounts/presentation/me.py:29) —
        토큰이 아예 없거나 서버가 401(만료/무효)이면 로그인 안 된 것으로 보고 ``None``.
        그 외 실패(서버 다운 등)는 감추지 않고 그대로 올린다 — "로그인 안 됨"과 "서버에
        연결할 수 없음"을 UI가 구분할 수 있게."""
        raw = self._store.get_settings()
        token = _effective_token(raw)
        if not token:
            return None
        api_base = raw.get("apiBase") or _DEFAULT_API_BASE
        try:
            _, body = _request({"apiBase": api_base, "token": token}, "GET", "/me")
        except PublishHttpError as exc:
            if exc.status == 401:
                return None
            raise
        return body


def run_smoke(window, timeout_s=5.0, poll_interval_s=0.1):
    """창 로드 완료 후 확인 순서:
      1) 마운트 — [contenteditable] 존재.
      2) 브리지 CRUD 왕복 — createChapter → saveChapter(html) → reorderChapters →
         (프로세스 재시작 없이) listChapters 로 순서, loadChapter 로 내용을 재확인.
      3) 원고 가져오기(4번 항목 참고).
      4) 스냅샷/되돌리기(P1 슬라이스6) — takeSnapshot → 내용 수정(saveChapter) →
         restoreSnapshot 으로 원복 확인 + 복원 직전 자동 스냅샷("복원 전 자동")이
         실제로 listSnapshots 에 남았는지까지 확인.

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

        # 캔버스(본문) 서체 확인 — P1 슬라이스2: article[data-juldoc] 에 Noto Serif KR
        # (ide-core/src/style.css 오버라이드 + theme.js 의 --hj-font-serif) 가 실제
        # computed style 에 반영됐는지. font-family 문자열에 'Noto Serif KR' 이 있으면 적용.
        canvas_font_family = window.evaluate_js(
            "(function () {"
            "  var el = document.querySelector('article[data-juldoc]');"
            "  if (!el) return null;"
            "  return getComputedStyle(el).fontFamily;"
            "})()"
        )
        results["canvasFontFamily"] = canvas_font_family
        results["canvasFontApplied"] = bool(
            canvas_font_family and "Noto Serif KR" in canvas_font_family
        )

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

        # 4) 원고 가져오기(P1 슬라이스3) — h1 2개짜리 임시 .md 를 실제로 import_file(path)
        #    왕복시켜 챕터 2개 추가·제목(h1 텍스트)·본문 일치를 확인한다. path 를 직접
        #    넘겨 파일 다이얼로그(사람 손 필요)를 건너뛴다 — app.py:import_file 참고.
        import_md_path = None
        try:
            tmp_dir = tempfile.mkdtemp(prefix="hanjul_ide_smoke_")
            import_md_path = str(Path(tmp_dir) / "smoke_import.md")
            Path(import_md_path).write_text(
                "# 스모크 1장\n\n스모크 1장 본문.\n\n# 스모크 2장\n\n스모크 2장 본문.\n",
                encoding="utf-8",
            )
        except Exception as exc:
            results["import_setup_error"] = repr(exc)

        import_result = None
        import_error = None
        import_done = False
        if import_md_path is not None:
            escaped_path = json.dumps(import_md_path)  # JS 문자열 리터럴로 안전하게 이스케이프
            window.evaluate_js(
                f"""
                window.__importDone = false;
                (async function () {{
                  try {{
                    const beforeImport = await window.pywebview.api.list_chapters();
                    const importResult = await window.pywebview.api.import_file({escaped_path});
                    const afterImport = await window.pywebview.api.list_chapters();
                    const firstChapter = await window.pywebview.api.load_chapter(importResult.chapterIds[0]);
                    const secondChapter = await window.pywebview.api.load_chapter(importResult.chapterIds[1]);
                    window.__importResult = {{
                      chaptersBeforeImport: beforeImport.length,
                      chaptersAfterImport: afterImport.length,
                      importedCount: importResult.importedCount,
                      chapterIdsLength: importResult.chapterIds.length,
                      firstTitle: firstChapter.title,
                      firstHtmlMatches: firstChapter.html.includes('스모크 1장 본문'),
                      secondTitle: secondChapter.title,
                      secondHtmlMatches: secondChapter.html.includes('스모크 2장 본문'),
                    }};
                  }} catch (e) {{
                    window.__importError = String(e && e.message ? e.message : e);
                  }} finally {{
                    window.__importDone = true;
                  }}
                }})();
                """
            )
            deadline = time.monotonic() + timeout_s
            while time.monotonic() < deadline:
                import_done = bool(window.evaluate_js("window.__importDone === true"))
                if import_done:
                    break
                time.sleep(poll_interval_s)
            import_result = window.evaluate_js("window.__importResult")
            import_error = window.evaluate_js("window.__importError")

        results["import_bridge_done_within_timeout"] = import_done
        results["import_result"] = import_result
        results["import_error"] = import_error

        # 5) 스냅샷/되돌리기(P1 슬라이스6) — 3) 단계에서 만든 스모크 챕터(createdId)를 재사용:
        #    지금 스냅샷 → 내용 수정 → 스냅샷으로 복원 → 원복 확인 + 복원 직전 자동
        #    스냅샷("복원 전 자동")이 실제로 남았는지까지 확인한다. 참고: 3) 단계의
        #    save_chapter 호출 자체가 이미 "최초 자동 스냅샷"(스냅샷 없음 → 즉시 생성)을
        #    한 번 만들어 두므로, 여기서는 절대 개수가 아니라 호출 전후 델타로 비교한다.
        window.evaluate_js(
            """
            window.__snapshotDone = false;
            (async function () {
              try {
                const chapterId = window.__smokeResult.createdId;
                const original = await window.pywebview.api.load_chapter(chapterId);
                const beforeTake = await window.pywebview.api.list_snapshots(chapterId);
                const taken = await window.pywebview.api.take_snapshot(chapterId, '스모크 라벨');
                const afterTake = await window.pywebview.api.list_snapshots(chapterId);
                const modifiedHtml = '<article data-juldoc="1"><p>스모크 수정본</p></article>';
                await window.pywebview.api.save_chapter(chapterId, { html: modifiedHtml });
                const afterModify = await window.pywebview.api.load_chapter(chapterId);
                const restored = await window.pywebview.api.restore_snapshot(taken.id);
                const afterRestore = await window.pywebview.api.list_snapshots(chapterId);
                window.__snapshotResult = {
                  snapshotsBeforeTake: beforeTake.length,
                  snapshotsAfterTake: afterTake.length,
                  takenLabelListed: afterTake.some((s) => s.id === taken.id && s.label === '스모크 라벨'),
                  modifiedHtmlApplied: afterModify.html.includes('스모크 수정본'),
                  restoredHtmlMatchesOriginal: restored.html === original.html,
                  snapshotsAfterRestoreCount: afterRestore.length,
                  restoreAutoSnapshotListed: afterRestore.some((s) => s.label === '복원 전 자동'),
                };
              } catch (e) {
                window.__snapshotError = String(e && e.message ? e.message : e);
              } finally {
                window.__snapshotDone = true;
              }
            })();
            """
        )
        deadline = time.monotonic() + timeout_s
        snapshot_done = False
        while time.monotonic() < deadline:
            snapshot_done = bool(window.evaluate_js("window.__snapshotDone === true"))
            if snapshot_done:
                break
            time.sleep(poll_interval_s)
        snapshot_result = window.evaluate_js("window.__snapshotResult")
        snapshot_error = window.evaluate_js("window.__snapshotError")
        results["snapshot_bridge_done_within_timeout"] = snapshot_done
        results["snapshot_result"] = snapshot_result
        results["snapshot_error"] = snapshot_error

        results["ok"] = bool(
            app_mounted
            and results.get("contenteditable_present")
            and results.get("canvasFontApplied")
            and done
            and smoke_result
            and not smoke_error
            and smoke_result.get("chaptersAfterCreate") == smoke_result.get("chaptersBeforeCreate", -1) + 1
            and smoke_result.get("firstIdMatchesCreated")
            and smoke_result.get("loadedStatus") == "DRAFT"
            and smoke_result.get("loadedHtmlMatches")
            and import_done
            and import_result
            and not import_error
            and import_result.get("chaptersAfterImport") == import_result.get("chaptersBeforeImport", -1) + 2
            and import_result.get("importedCount") == 2
            and import_result.get("chapterIdsLength") == 2
            and import_result.get("firstTitle") == "스모크 1장"
            and import_result.get("firstHtmlMatches")
            and import_result.get("secondTitle") == "스모크 2장"
            and import_result.get("secondHtmlMatches")
            and snapshot_done
            and snapshot_result
            and not snapshot_error
            and snapshot_result.get("snapshotsAfterTake") == snapshot_result.get("snapshotsBeforeTake", -1) + 1
            and snapshot_result.get("takenLabelListed")
            and snapshot_result.get("modifiedHtmlApplied")
            and snapshot_result.get("restoredHtmlMatchesOriginal")
            and snapshot_result.get("snapshotsAfterRestoreCount")
            == snapshot_result.get("snapshotsAfterTake", -1) + 1
            and snapshot_result.get("restoreAutoSnapshotListed")
        )
    except Exception as exc:  # 스모크 자체가 실패한 원인을 있는 그대로 남긴다.
        results["error"] = repr(exc)
        results["ok"] = False

    print("SMOKE_RESULT " + json.dumps(results, ensure_ascii=False))
    sys.stdout.flush()
    window.destroy()


def run_perf(window, timeout_s=60.0, poll_interval_s=0.1):
    """L0 성능 계측 하네스 구동(dc-81277381) — packages/ide-core/src/perfMain.js 가 심어둔
    ``window.__perfHarness.run()`` 을 완료 플래그 폴링으로 기다린다. run_smoke() 와 동일한
    이유(lr-9a45e6e4): pywebview evaluate_js 는 Promise 를 동기적으로 풀지 못해 완료 전
    값을 훔쳐보면 "{}" 를 반환하는 레이스가 있다 — 그래서 JS 쪽 완료 플래그를 심어두고
    그 플래그가 설 때까지 폴링한다.

    합성 챕터 3종(1만/3만/10만 자) × content-visibility on/off 총 6 설정 × 마운트/직렬화/
    입력지연/스크롤 4항목을 실측하는 하네스라 --smoke 보다 오래 걸릴 수 있어 기본
    타임아웃을 60초로 넉넉히 잡는다."""
    results = {"ok": False}
    try:
        deadline = time.monotonic() + timeout_s
        ready = False
        while time.monotonic() < deadline:
            ready = bool(window.evaluate_js("window.__perfHarness !== undefined"))
            if ready:
                break
            time.sleep(poll_interval_s)
        results["harness_ready_within_timeout"] = ready

        window.evaluate_js(
            """
            window.__perfDone = false;
            (async function () {
              try {
                window.__perfResult = await window.__perfHarness.run();
              } catch (e) {
                window.__perfError = String(e && e.message ? e.message : e);
              } finally {
                window.__perfDone = true;
              }
            })();
            """
        )

        deadline = time.monotonic() + timeout_s
        done = False
        while time.monotonic() < deadline:
            done = bool(window.evaluate_js("window.__perfDone === true"))
            if done:
                break
            time.sleep(poll_interval_s)
        results["perf_done_within_timeout"] = done

        perf_result = window.evaluate_js("window.__perfResult")
        perf_error = window.evaluate_js("window.__perfError")
        results["perf_result"] = perf_result
        results["perf_error"] = perf_error
        # 완료 못 해도(타임아웃) 어디까지 진행됐는지 진단 — perfMain.js:__perfProgress.
        results["perf_progress"] = window.evaluate_js("window.__perfProgress")
        results["ok"] = bool(ready and done and perf_result and not perf_error)
    except Exception as exc:  # 하네스 자체가 실패한 원인을 있는 그대로 남긴다.
        results["error"] = repr(exc)
        results["ok"] = False

    print("PERF_RESULT " + json.dumps(results, ensure_ascii=False))
    sys.stdout.flush()

    PERF_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    PERF_REPORT_PATH.write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    window.destroy()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="창을 띄운 뒤 자동으로 마운트/Host Port CRUD 왕복을 확인하고 종료",
    )
    parser.add_argument(
        "--perf",
        action="store_true",
        help="L0 성능 계측 하네스(dc-81277381)를 숨김창으로 구동 — PERF_RESULT stdout + "
        "desktop/perf/report.json 저장 후 종료. Store/js_api 없이 packages/ide-core의 "
        "perf.html(mountEditor 단독)만 로드한다.",
    )
    parser.add_argument(
        "--perf-timeout",
        type=float,
        default=60.0,
        help="--perf 각 단계(하네스 준비/완료) 대기 타임아웃(초, 기본 60).",
    )
    parser.add_argument(
        "--db",
        default=None,
        help="대체 SQLite 파일 경로(검증/반복 실행용). 기본은 desktop/data/ide.db.",
    )
    args = parser.parse_args()

    if args.perf:
        # --perf 는 Store/js_api 가 전혀 필요 없다(챕터/호스트 브리지 미개입, perfMain.js
        # 가 packages/doc mountEditor 를 직접 합성 데이터로 구동) — 그래서 DIST_INDEX 존재
        # 확인·Store 생성 분기 전체를 건너뛴다.
        if not PERF_INDEX.exists():
            print(
                f"빌드 산출물 없음: {PERF_INDEX}\n"
                "먼저 저장소 루트에서 `npm install && npm run build -w packages/ide-core` 를 실행하세요.",
                file=sys.stderr,
            )
            sys.exit(1)
        window = webview.create_window(
            "한줄 IDE — L0 성능 계측",
            str(PERF_INDEX),
            width=900,
            height=700,
            hidden=True,  # 하네스는 항상 숨김창 — 창 깜빡임 금지 (lr-9a45e6e4)
        )
        window.events.loaded += lambda: run_perf(window, timeout_s=args.perf_timeout)
        webview.start()
        return

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
    api._window = window  # import_file() 의 파일 다이얼로그가 창 핸들을 필요로 함

    if args.smoke:
        window.events.loaded += lambda: run_smoke(window)

    webview.start()


if __name__ == "__main__":
    main()
