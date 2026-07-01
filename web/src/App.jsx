import { Route, Routes, useLocation } from 'react-router-dom';

import { Footer } from './components/Footer';
import { Header } from './components/Header';
import { MobileTabBar } from './components/MobileTabBar';
import { useIsMobile } from './hooks/useIsMobile';
import { AuthCallbackPage } from './pages/AuthCallbackPage';
import { LegalPage } from './pages/LegalPage';
import { NotFoundPage } from './pages/NotFoundPage';
import { AuthorPage } from './pages/AuthorPage';
import { B2BPlanPage } from './pages/B2BPlanPage';
import { BookDetailPage } from './pages/BookDetailPage';
import { CampaignDetailPage } from './pages/CampaignDetailPage';
import { CampaignStudioPage } from './pages/CampaignStudioPage';
import { ReviewCopyReviewPage } from './pages/ReviewCopyReviewPage';
import { LibraryPage } from './pages/LibraryPage';
import { LoginPage } from './pages/LoginPage';
import { NotificationsPage } from './pages/NotificationsPage';
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
  const isMobile = useIsMobile();
  // 에디터(/write)는 집중 글쓰기 도구 → 마케팅 헤더 숨김(전체화면, 자체 툴바 사용).
  const hideHeader = pathname.startsWith('/write/');
  // 모바일 하단 탭바가 가리지 않도록 스크롤 영역에 여백(몰입화면 제외).
  const immersive = pathname.startsWith('/write/') || pathname.startsWith('/read/');
  const bottomPad = isMobile && !immersive ? 72 : 0;

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {!hideHeader && <Header />}
      {/* 헤더는 고정, 그 아래 영역이 스크롤. 일반 페이지는 이 영역이 스크롤되고,
          글쓰기 페이지는 height:100% 자식이 내부에서 사이드바/에디터를 따로 스크롤시킨다. */}
      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', paddingBottom: bottomPad }}>
        <Routes>
        <Route path="/" element={<StorePage />} />
        <Route path="/books/:id" element={<BookDetailPage />} />
        <Route path="/authors/:id" element={<AuthorPage />} />
        <Route path="/read/:id" element={<ReaderPage />} />
        <Route path="/library" element={<LibraryPage />} />
        <Route path="/notifications" element={<NotificationsPage />} />
        <Route path="/studio" element={<StudioPage />} />
        <Route path="/studio/campaigns" element={<CampaignStudioPage />} />
        <Route path="/studio/:id" element={<StudioEditorPage />} />
        <Route path="/reviewers" element={<ReviewersPage />} />
        <Route path="/reviewers/business" element={<B2BPlanPage />} />
        <Route path="/campaigns/:id" element={<CampaignDetailPage />} />
        <Route path="/campaigns/:id/review" element={<ReviewCopyReviewPage />} />
        <Route path="/reviewer/activity" element={<ReviewerActivityPage />} />
        <Route path="/write/:id" element={<WritePage />} />
        <Route path="/pricing" element={<PricingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/payment/result" element={<PaymentResultPage />} />
        <Route path="/auth/callback" element={<AuthCallbackPage />} />
        <Route path="/legal/:slug" element={<LegalPage />} />
        <Route path="*" element={<NotFoundPage />} />
        </Routes>
        {/* 사업자정보·법률 푸터 — 몰입화면(리더·에디터) 제외 */}
        {!immersive && <Footer />}
      </div>
      <MobileTabBar />
    </div>
  );
}
