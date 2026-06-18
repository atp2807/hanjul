import { Route, Routes } from 'react-router-dom';

import { Header } from './components/Header';
import { BookDetailPage } from './pages/BookDetailPage';
import { ReaderPage } from './pages/ReaderPage';
import { StorePage } from './pages/StorePage';

export default function App() {
  return (
    <>
      <Header />
      <Routes>
        <Route path="/" element={<StorePage />} />
        <Route path="/books/:id" element={<BookDetailPage />} />
        <Route path="/read/:id" element={<ReaderPage />} />
      </Routes>
    </>
  );
}
