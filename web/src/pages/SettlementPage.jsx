import { useEffect, useState } from 'react';

import { useAuth } from '../auth/AuthContext';
import {
  getBankAccount,
  getPayable,
  getPayouts,
  requestPayout,
  setBankAccount,
} from '../services/api/payouts';
import { T } from '../theme';

const STATUS_LABEL = {
  REQUESTED: { text: '신청됨', tone: '#8e6911', bg: '#fff3da' },
  APPROVED: { text: '승인됨', tone: '#4c66bf', bg: '#e8eeff' },
  PAID: { text: '지급완료', tone: '#297961', bg: '#e3f3ec' },
  REJECTED: { text: '반려됨', tone: '#c63c23', bg: '#fdeeea' },
};

function Card({ title, children, style }) {
  return (
    <div style={{ background: T.surface, borderRadius: 18, padding: '24px 26px', marginBottom: 16, ...style }}>
      {title && <div style={{ fontSize: 16, fontWeight: 800, color: T.ink, marginBottom: 16 }}>{title}</div>}
      {children}
    </div>
  );
}

export function SettlementPage() {
  const { user } = useAuth();
  const [account, setAccount] = useState(null);
  const [payable, setPayable] = useState(null);
  const [payouts, setPayouts] = useState([]);
  const [form, setForm] = useState({ holderName: '', bank: '', accountNo: '' });
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState('');
  const [msg, setMsg] = useState('');

  async function load() {
    const [a, p, list] = await Promise.all([getBankAccount(), getPayable(), getPayouts()]);
    setAccount(a);
    setPayable(p);
    setPayouts(list);
    if (!a) setEditing(true);
  }

  useEffect(() => {
    if (user) load().catch(() => setError('불러오기에 실패했어요.'));
  }, [user]);

  if (!user) {
    return <div style={{ padding: '54px 24px', textAlign: 'center', color: T.muted }}>로그인이 필요해요.</div>;
  }

  async function saveAccount(e) {
    e.preventDefault();
    setError('');
    try {
      const a = await setBankAccount(form.holderName, form.bank, form.accountNo);
      setAccount(a);
      setEditing(false);
      setForm({ holderName: '', bank: '', accountNo: '' });
    } catch (err) {
      setError(err.status === 422 ? '계좌 정보를 확인해 주세요.' : '저장 실패');
    }
  }

  async function withdraw() {
    setError('');
    setMsg('');
    try {
      await requestPayout();
      setMsg('출금을 신청했어요. 검토 후 지급됩니다.');
      await load();
    } catch (err) {
      setError(err.status === 422 ? '출금 가능한 정산 잔액이 없거나 계좌가 없어요.' : '신청 실패');
    }
  }

  const inputStyle = {
    width: '100%', font: T.font, fontSize: 14, padding: '10px 12px',
    borderRadius: 10, border: `1px solid ${T.border}`, marginTop: 6, boxSizing: 'border-box',
  };

  return (
    <div style={{ padding: '40px 24px 80px' }}>
      <div style={{ maxWidth: 680, margin: '0 auto' }}>
        <h1 style={{ margin: '0 0 6px', fontSize: 26, fontWeight: 800, color: T.ink, letterSpacing: '-0.02em' }}>
          정산·출금
        </h1>
        <p style={{ fontSize: 14, color: T.muted, margin: '0 0 24px' }}>
          판매 정산금을 등록한 계좌로 출금 신청할 수 있어요. (개인 작가는 3.3% 원천징수 후 지급)
        </p>

        {/* 출금 가능액 */}
        <Card style={{ background: T.ink }}>
          <div style={{ fontSize: 13, color: T.inkSoft }}>출금 가능액</div>
          <div style={{ fontSize: 34, fontWeight: 800, color: '#fff', marginTop: 6, letterSpacing: '-0.02em' }}>
            {payable ? `${payable.netAmt.toLocaleString()}원` : '–'}
          </div>
          {payable && payable.netAmt > 0 && (
            <div style={{ fontSize: 12.5, color: T.inkSoft, marginTop: 6 }}>
              {payable.orderCount}건 · 원천징수 {payable.withholdingAmt.toLocaleString()}원 차감 후
            </div>
          )}
          <button
            onClick={withdraw}
            disabled={!payable || payable.netAmt <= 0 || !account}
            style={{
              marginTop: 16, padding: '11px 22px', borderRadius: 11, border: 'none',
              background: (!payable || payable.netAmt <= 0 || !account) ? 'rgba(255,255,255,0.25)' : '#fff',
              color: (!payable || payable.netAmt <= 0 || !account) ? T.inkSoft : T.ink,
              fontSize: 14, fontWeight: 700, cursor: (!payable || payable.netAmt <= 0 || !account) ? 'default' : 'pointer',
            }}
          >
            출금 신청
          </button>
          {msg && <div style={{ fontSize: 13, color: '#c8f0e2', marginTop: 10 }}>{msg}</div>}
        </Card>

        {/* 계좌 */}
        <Card title="출금 계좌">
          {!editing && account ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ fontSize: 14, color: T.textStrong }}>
                {account.bank} · {account.accountNoMasked} · {account.holderName}
              </div>
              <button onClick={() => setEditing(true)} style={{
                padding: '8px 14px', borderRadius: 10, border: `1px solid ${T.border}`,
                background: T.surface, color: T.textMid, fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>
                변경
              </button>
            </div>
          ) : (
            <form onSubmit={saveAccount}>
              <label style={{ display: 'block', fontSize: 13, color: T.textSoft }}>예금주
                <input style={inputStyle} value={form.holderName} required maxLength={100}
                  onChange={(e) => setForm({ ...form, holderName: e.target.value })} placeholder="홍길동" />
              </label>
              <label style={{ display: 'block', fontSize: 13, color: T.textSoft, marginTop: 12 }}>은행
                <input style={inputStyle} value={form.bank} required maxLength={20}
                  onChange={(e) => setForm({ ...form, bank: e.target.value })} placeholder="국민은행" />
              </label>
              <label style={{ display: 'block', fontSize: 13, color: T.textSoft, marginTop: 12 }}>계좌번호
                <input style={inputStyle} value={form.accountNo} required minLength={6} maxLength={30}
                  onChange={(e) => setForm({ ...form, accountNo: e.target.value })} placeholder="숫자만" />
              </label>
              <button type="submit" style={{
                marginTop: 16, padding: '10px 20px', borderRadius: 11, border: 'none',
                background: T.ink, color: T.inkText, fontSize: 14, fontWeight: 700, cursor: 'pointer' }}>
                계좌 저장
              </button>
            </form>
          )}
        </Card>

        {error && <div style={{ color: '#c63c23', fontSize: 13, marginBottom: 12 }}>{error}</div>}

        {/* 출금 내역 */}
        <Card title="출금 내역">
          {payouts.length === 0 && <div style={{ color: T.muted, fontSize: 13 }}>출금 내역이 없어요.</div>}
          {payouts.map((p) => {
            const st = STATUS_LABEL[p.status] || { text: p.status, tone: T.muted, bg: T.tint };
            return (
              <div key={p.id} style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '13px 0', borderBottom: `1px solid ${T.borderSoft}` }}>
                <div>
                  <div style={{ fontSize: 15, fontWeight: 700, color: T.textStrong }}>{p.netAmt.toLocaleString()}원</div>
                  <div style={{ fontSize: 12, color: T.muted }}>
                    신청 {new Date(p.requestedAt).toLocaleDateString()} · 원천징수 {p.withholdingAmt.toLocaleString()}원
                  </div>
                </div>
                <span style={{ padding: '4px 11px', borderRadius: 999, fontSize: 12, fontWeight: 700, color: st.tone, background: st.bg }}>
                  {st.text}
                </span>
              </div>
            );
          })}
        </Card>
      </div>
    </div>
  );
}
