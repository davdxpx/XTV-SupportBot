import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Route, Routes, Navigate } from 'react-router-dom';

import { Layout } from '@/components/Layout';
import { Login } from '@/pages/Login';
import { Dashboard } from '@/pages/Dashboard';
import { Tickets } from '@/pages/Tickets';
import { hasCredentials } from '@/lib/api';
import { bootTelegram } from '@/lib/telegram';

// Announce readiness to Telegram + expand the viewport so the SPA
// renders full-height inside the Mini-App. No-op in a regular browser.
bootTelegram();

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 10_000,
      refetchOnWindowFocus: false,
    },
  },
});

function RequireAuth({ children }: { children: React.ReactNode }) {
  return hasCredentials() ? <>{children}</> : <Navigate to="/login" replace />;
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/"
            element={
              <RequireAuth>
                <Layout />
              </RequireAuth>
            }
          >
            <Route index element={<Dashboard />} />
            <Route path="tickets" element={<Tickets />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>
);
