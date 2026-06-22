// 최소 y-websocket 호환 동기화 서버 (CRDT 릴레이 + 룸별 서버 Y.Doc).
// @y/websocket-server 의존성 깨짐 + y-websocket v3 서버 미포함 → ws + y-protocols 로 직접 구현(표준 패턴).
// 룸 = /write/:id 의 docId. 인메모리만(디스크 영속·prod 배포는 별도 슬라이스/배치).
import * as decoding from 'lib0/decoding';
import * as encoding from 'lib0/encoding';
import * as sync from 'y-protocols/sync';
import { WebSocketServer } from 'ws';
import * as Y from 'yjs';

const PORT = Number(process.env.SYNC_PORT || 1234);
const MSG_SYNC = 0;
const MSG_AWARENESS = 1;

const rooms = new Map(); // name -> { doc, conns:Set<ws> }

function getRoom(name) {
  let r = rooms.get(name);
  if (r) return r;
  const doc = new Y.Doc();
  const conns = new Set();
  // 서버 doc 변경 → 모든 연결에 update 브로드캐스트
  doc.on('update', (update) => {
    const enc = encoding.createEncoder();
    encoding.writeVarUint(enc, MSG_SYNC);
    sync.writeUpdate(enc, update);
    const msg = encoding.toUint8Array(enc);
    conns.forEach((ws) => send(ws, msg));
  });
  r = { doc, conns };
  rooms.set(name, r);
  return r;
}

function send(ws, msg) {
  try {
    if (ws.readyState === 1) ws.send(msg);
  } catch {
    /* 닫힌 소켓 무시 */
  }
}

const wss = new WebSocketServer({ port: PORT });

wss.on('connection', (ws, req) => {
  ws.binaryType = 'arraybuffer';
  const name = decodeURIComponent((req.url || '/').slice(1).split('?')[0]) || 'default';
  const room = getRoom(name);
  room.conns.add(ws);

  ws.on('message', (data) => {
    try {
      const dec = decoding.createDecoder(new Uint8Array(data));
      const type = decoding.readVarUint(dec);
      if (type === MSG_SYNC) {
        // syncStep1→서버상태로 응답, syncStep2/update→서버 doc 반영(→브로드캐스트)
        const enc = encoding.createEncoder();
        encoding.writeVarUint(enc, MSG_SYNC);
        sync.readSyncMessage(dec, enc, room.doc, ws);
        if (encoding.length(enc) > 1) send(ws, encoding.toUint8Array(enc));
      } else if (type === MSG_AWARENESS) {
        // 인지(커서)는 서버 상태 없이 다른 피어로 중계만
        const raw = new Uint8Array(data);
        room.conns.forEach((other) => {
          if (other !== ws) send(other, raw);
        });
      }
    } catch {
      // 잘못된 프레임 하나가 서버 전체를 죽이지 않게 격리 — 해당 소켓만 종료
      try {
        ws.close();
      } catch {
        /* already closed */
      }
    }
  });

  // 소켓 레벨 에러(ECONNRESET 등)도 프로세스 크래시로 번지지 않게
  ws.on('error', () => {
    try {
      ws.close();
    } catch {
      /* noop */
    }
  });

  ws.on('close', () => {
    room.conns.delete(ws);
    if (room.conns.size === 0) rooms.delete(name); // 인메모리 정리
  });

  // 접속 즉시 서버가 syncStep1 발신 → 클라가 자기 상태로 응답
  const enc = encoding.createEncoder();
  encoding.writeVarUint(enc, MSG_SYNC);
  sync.writeSyncStep1(enc, room.doc);
  send(ws, encoding.toUint8Array(enc));
});

// eslint-disable-next-line no-console
console.log(`[sync] y-websocket relay on :${PORT}`);
