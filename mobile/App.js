import { useCallback, useRef, useState } from 'react';
import { SafeAreaView, StyleSheet, Text, View } from 'react-native';
import { WebView } from 'react-native-webview';
import * as FileSystem from 'expo-file-system';
import { EDITOR_HTML } from './src/editorHtml';

// 한줄 IDE 모바일 스파이크(ⓑ) — packages/doc 에디터(EDITOR_HTML, mobile/webapp-spike 가 빌드한
// 단일 인라인 HTML)를 RN WebView 에 로드하고 postMessage 브리지 왕복을 확인하는 최소 앱.
// 목적 = iPad(iOS WKWebView)에서 한글 IME 입력이 정상인지 Expo Go 로 직접 검증(README.md 체크리스트).
//
// 브리지 왕복 (웹 쪽 카운터파트: mobile/webapp-spike/src/main.js):
//  1) 웹 페이지가 window.ReactNativeWebView.postMessage(JSON.stringify({type:'save', saveId, html}))
//     를 보낸다 — 이건 "보냈다"만 보장하지, RN 이 실제로 파일에 썼는지는 모른다.
//  2) 아래 handleMessage 가 받아서 expo-file-system 으로 기록.
//  3) 기록이 끝난 *뒤에* injectJavaScript 로 웹 페이지의 window.__onSaveResult(saveId, ok, meta) 를
//     호출한다 — 웹 쪽 Promise 는 이 콜백이 올 때까지 대기하므로, 파일 쓰기가 끝나기 전에 성공을
//     가정하는 동기 반환 실수(P0 ⓐ 에서 겪은 교훈)를 여기서도 반복하지 않는다.
const SAVE_FILE_URI = `${FileSystem.documentDirectory}hanjul-ide-spike-editor.html`;

export default function App() {
  const webviewRef = useRef(null);
  const [nativeStatus, setNativeStatus] = useState('네이티브: 저장 대기 중');
  const [bridgeCount, setBridgeCount] = useState(0);

  const respondToWeb = useCallback((saveId, ok, meta) => {
    // 문자열 하나를 evaluate 하는 것뿐이라 saveId/ok 는 리터럴로, meta 는 JSON 으로 안전 임베드.
    const script = `window.__onSaveResult && window.__onSaveResult(${saveId}, ${ok}, ${JSON.stringify(meta)}); true;`;
    webviewRef.current?.injectJavaScript(script);
  }, []);

  const handleMessage = useCallback(
    async (event) => {
      let data;
      try {
        data = JSON.parse(event.nativeEvent.data);
      } catch {
        return; // 알 수 없는 메시지 포맷 — 향후 다른 타입 공존 대비, 조용히 무시.
      }
      setBridgeCount((n) => n + 1);
      if (data.type !== 'save') return;

      const { saveId, html } = data;
      try {
        await FileSystem.writeAsStringAsync(SAVE_FILE_URI, html ?? '', {
          encoding: FileSystem.EncodingType.UTF8,
        });
        const savedAt = new Date().toLocaleTimeString('ko-KR', { hour12: false });
        const bytes = typeof html === 'string' ? html.length : 0;
        setNativeStatus(`네이티브 저장 완료 · ${savedAt} (${bytes} chars)\n${SAVE_FILE_URI}`);
        respondToWeb(saveId, true, { savedAt, bytes });
      } catch (err) {
        const message = String(err?.message || err);
        setNativeStatus(`네이티브 저장 실패: ${message}`);
        respondToWeb(saveId, false, { error: message });
      }
    },
    [respondToWeb],
  );

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.nativeBar}>
        <Text style={styles.nativeTitle}>한줄 IDE 모바일 스파이크 (ⓑ WebView 에디터)</Text>
        <Text style={styles.nativeStatus}>{nativeStatus}</Text>
        <Text style={styles.nativeMeta}>브리지 메시지 수신: {bridgeCount}회</Text>
      </View>
      <WebView
        ref={webviewRef}
        originWhitelist={['*']}
        source={{ html: EDITOR_HTML }}
        onMessage={handleMessage}
        style={styles.webview}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0e4a5c' },
  nativeBar: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    backgroundColor: '#0e4a5c',
  },
  nativeTitle: { color: '#eafaf5', fontWeight: '700', fontSize: 14 },
  nativeStatus: { color: '#eafaf5', fontSize: 12, marginTop: 4 },
  nativeMeta: { color: '#9fd8cd', fontSize: 11, marginTop: 4 },
  webview: { flex: 1, backgroundColor: '#f3faf8' },
});
