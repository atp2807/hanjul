"""한줄 IDE P0 스파이크 — pywebview 셸 안에서 packages/doc 에디터를 띄우고
JS<->Python 브리지 왕복을 검증한다.

목적: macOS WKWebView 위에서 한글 IME 입력이 정상인지 사람이 손으로 확인할 수 있는
실행물 + `--smoke` 로 브리지/마운트 자동 확인.

실행:
    cd desktop && .venv/bin/python app.py            # GUI 창
    cd desktop && .venv/bin/python app.py --smoke     # 자동 스모크(수 초 내 종료)
"""

import argparse
import json
import sys
import time
from pathlib import Path

import webview

BASE_DIR = Path(__file__).resolve().parent
DIST_INDEX = BASE_DIR / "webapp" / "dist" / "index.html"
SPIKE_DATA_DIR = BASE_DIR / "spike_data"
CHAPTER_FILE = SPIKE_DATA_DIR / "chapter.html"


class Api:
    """js_api 로 노출되는 Python 쪽 브리지. SQLite 는 P1 — 스파이크는 파일로 충분."""

    def save_chapter(self, html):
        SPIKE_DATA_DIR.mkdir(parents=True, exist_ok=True)
        CHAPTER_FILE.write_text(html, encoding="utf-8")
        saved_at = time.strftime("%Y-%m-%dT%H:%M:%S")
        return {
            "saved_at": saved_at,
            "bytes": len(html.encode("utf-8")),
        }


def run_smoke(window, timeout_s=5.0, poll_interval_s=0.1):
    """창 로드 완료 후 ①contenteditable 존재 ②JS->Python 브리지 왕복을 확인하고
    결과를 stdout 한 줄(JSON)로 출력한 뒤 창을 닫는다.

    주의: window.pywebview.api.save_chapter(...) 는 JS 쪽에서 Promise 를 반환하고,
    실제 Python 메서드는 별도 스레드에서 실행된다(pywebview util.js_bridge_call).
    evaluate_js 가 콜백 없이 Promise 를 즉시 JSON.stringify 하면 빈 객체 "{}" 가
    나오고(Promise 는 열거 가능한 own property 가 없음) 완료를 보장하지 않는다.
    그래서 JS 쪽에 완료 플래그(window.__bridgeDone/__bridgeResult) 를 심어두고
    그 플래그가 설 때까지 폴링한다 — 이게 실제 왕복 완료를 보는 유일한 결정적 신호.
    """
    results = {}
    try:
        has_editor = window.evaluate_js(
            'document.querySelector("[contenteditable]") !== null'
        )
        results["contenteditable_present"] = bool(has_editor)

        has_ctrl = window.evaluate_js('typeof window.__editorCtrl !== "undefined"')
        results["editor_controller_present"] = bool(has_ctrl)

        # 브리지 왕복 트리거(fire-and-forget) — 결과/완료는 JS 쪽 전역 플래그에 남긴다.
        window.evaluate_js(
            """
            window.__bridgeDone = false;
            window.pywebview.api.save_chapter(
              document.querySelector('[contenteditable]').outerHTML
            ).then(function (r) {
              window.__bridgeResult = r;
              window.__bridgeDone = true;
            }).catch(function (e) {
              window.__bridgeError = String(e);
              window.__bridgeDone = true;
            });
            """
        )

        deadline = time.monotonic() + timeout_s
        done = False
        while time.monotonic() < deadline:
            done = bool(window.evaluate_js("window.__bridgeDone === true"))
            if done:
                break
            time.sleep(poll_interval_s)
        results["bridge_call_done_within_timeout"] = done

        bridge_result = window.evaluate_js("window.__bridgeResult")
        bridge_error = window.evaluate_js("window.__bridgeError")
        results["bridge_call_result"] = bridge_result
        results["bridge_call_error"] = bridge_error

        results["chapter_file_exists"] = CHAPTER_FILE.exists()
        if CHAPTER_FILE.exists():
            results["chapter_file_bytes"] = CHAPTER_FILE.stat().st_size
            results["chapter_file_preview"] = CHAPTER_FILE.read_text(encoding="utf-8")[:80]

        results["ok"] = bool(
            results.get("contenteditable_present")
            and results.get("editor_controller_present")
            and done
            and bridge_result
            and not bridge_error
            and results.get("chapter_file_exists")
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
        help="창을 띄운 뒤 자동으로 브리지/마운트를 확인하고 종료",
    )
    args = parser.parse_args()

    if not DIST_INDEX.exists():
        print(
            f"빌드 산출물 없음: {DIST_INDEX}\n"
            "먼저 `cd desktop/webapp && npm install && npm run build` 를 실행하세요.",
            file=sys.stderr,
        )
        sys.exit(1)

    api = Api()
    window = webview.create_window(
        "한줄 IDE 스파이크",
        str(DIST_INDEX),
        js_api=api,
        width=1000,
        height=800,
    )

    if args.smoke:
        window.events.loaded += lambda: run_smoke(window)

    webview.start(debug=args.smoke)


if __name__ == "__main__":
    main()
