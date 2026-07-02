import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { ErrorBoundary } from '@hanjul/lib';

import App from './App.jsx';
import { OpsAuthProvider } from './auth.jsx';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ErrorBoundary>
      <BrowserRouter>
        <OpsAuthProvider>
          <App />
        </OpsAuthProvider>
      </BrowserRouter>
    </ErrorBoundary>
  </StrictMode>,
);
