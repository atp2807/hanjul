import { Route, Routes } from 'react-router-dom';

import { Header } from './components/Header';
import { AuthCallbackPage } from './pages/AuthCallbackPage';
import { BookDetailPage } from './pages/BookDetailPage';
import { LibraryPage } from './pages/LibraryPage';
import { ReaderPage } from './pages/ReaderPage';
import { StorePage } from './pages/StorePage';
import { StudioEditorPage } from './pages/StudioEditorPage';
import { StudioPage } from './pages/StudioPage';

export default function App() {
  return (
    <>
      <Header />
      <Routes>
        <Route path="/" element={<StorePage />} />
        <Route path="/books/:id" element={<BookDetailPage />} />
        <Route path="/read/:id" element={<ReaderPage />} />
        <Route path="/library" element={<LibraryPage />} />
        <Route path="/studio" element={<StudioPage />} />
        <Route path="/studio/:id" element={<StudioEditorPage />} />
        <Route path="/auth/callback" element={<AuthCallbackPage />} />
      </Routes>
    </>
  );
}
