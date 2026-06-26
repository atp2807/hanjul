import { Route, Routes, useLocation } from 'react-router-dom';

import { Header } from './components/Header';
import { AuthCallbackPage } from './pages/AuthCallbackPage';
import { AuthorPage } from './pages/AuthorPage';
import { BookDetailPage } from './pages/BookDetailPage';
import { CampaignDetailPage } from './pages/CampaignDetailPage';
import { CampaignStudioPage } from './pages/CampaignStudioPage';
import { LibraryPage } from './pages/LibraryPage';
import { LoginPage } from './pages/LoginPage';
import { PaymentResultPage } from './pages/PaymentResultPage';
import { PricingPage } from './pages/PricingPage';
import { ReaderPage } from './pages/ReaderPage';
import { ReviewerActivityPage } from './pages/ReviewerActivityPage';
import { ReviewersPage } from './pages/ReviewersPage';
import { StorePage } from './pages/StorePage';
import { StudioEditorPage } from './pages/StudioEditorPage';
import { StudioPage } from './pages/StudioPage';
import { WritePage } from './pages/WritePage';

export default function App() {
  const { pathname } = useLocation();
  // 에디터(/write)는 집중 글쓰기 도구 → 마케팅 헤더 숨김(전체화면, 자체 툴바 사용).
  const hideHeader = pathname.startsWith('/write/');

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {!hideHeader && <Header />}
      {/* 헤더는 고정, 그 아래 영역이 스크롤. 일반 페이지는 이 영역이 스크롤되고,
          글쓰기 페이지는 height:100% 자식이 내부에서 사이드바/에디터를 따로 스크롤시킨다. */}
      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto' }}>
        <Routes>
        <Route path="/" element={<StorePage />} />
        <Route path="/books/:id" element={<BookDetailPage />} />
        <Route path="/authors/:id" element={<AuthorPage />} />
        <Route path="/read/:id" element={<ReaderPage />} />
        <Route path="/library" element={<LibraryPage />} />
        <Route path="/studio" element={<StudioPage />} />
        <Route path="/studio/campaigns" element={<CampaignStudioPage />} />
        <Route path="/studio/:id" element={<StudioEditorPage />} />
        <Route path="/reviewers" element={<ReviewersPage />} />
        <Route path="/campaigns/:id" element={<CampaignDetailPage />} />
        <Route path="/reviewer/activity" element={<ReviewerActivityPage />} />
        <Route path="/write/:id" element={<WritePage />} />
        <Route path="/pricing" element={<PricingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/payment/result" element={<PaymentResultPage />} />
        <Route path="/auth/callback" element={<AuthCallbackPage />} />
        </Routes>
      </div>
    </div>
  );
}
