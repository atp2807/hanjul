import { Navigate, Route, Routes } from 'react-router-dom';

import { useOps } from './auth.jsx';
import Layout from './Layout.jsx';
import { T } from './theme';
import Accounts from './pages/Accounts.jsx';
import Dashboard from './pages/Dashboard.jsx';
import Login from './pages/Login.jsx';
import Moderation from './pages/Moderation.jsx';
import Payouts from './pages/Payouts.jsx';
import Reports from './pages/Reports.jsx';

function Splash() {
  return (
    <div style={{ display: 'grid', placeItems: 'center', height: '100vh', color: T.muted }}>
      불러오는 중…
    </div>
  );
}

function RequireAuth({ children }) {
  const { operator, loading } = useOps();
  if (loading) return <Splash />;
  if (!operator) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route path="/" element={<Dashboard />} />
        <Route path="/moderation" element={<Moderation />} />
        <Route path="/reports" element={<Reports />} />
        <Route path="/accounts" element={<Accounts />} />
        <Route path="/payouts" element={<Payouts />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
