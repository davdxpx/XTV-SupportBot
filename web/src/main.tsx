import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import { BrowserRouter, Route, Routes, Navigate } from 'react-router-dom';

import { Layout } from '@/components/Layout';
import { UserLayout } from '@/components/UserLayout';
import { Login } from '@/pages/Login';
import { Dashboard } from '@/pages/Dashboard';
import { Tickets } from '@/pages/Tickets';
import { UserHome } from '@/pages/user/Home';
import { NewTicket } from '@/pages/user/NewTicket';
import { MyTickets } from '@/pages/user/MyTickets';
import { TicketDetail } from '@/pages/user/TicketDetail';
import { UserSettings } from '@/pages/user/Settings';
import { getMe, hasCredentials } from '@/lib/api';
import { bootTelegram, isInsideTelegram } from '@/lib/telegram';

// Tell Telegram we're ready + expand the viewport so the Mini-App
// renders full-height. No-op outside Telegram.
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

/**
 * Root switcher — the /api/v1/me probe tells us whether to render
 * the admin console (API-key login or Telegram admin) or the
 * end-user Mini-App (any Telegram user). The old admin Layout
 * stays reachable at /admin/* so an admin inside Telegram can
 * jump to the full dashboard.
 */
function Root() {
  const { data: me, isLoading } = useQuery({ queryKey: ['me'], queryFn: getMe });
  if (isLoading) return <div style={{ padding: 40 }}>Loading…</div>;

  // Admins on desktop browser get the power-user layout; Telegram
  // users (admin or not) default to the touch-friendly Mini-App UX.
  if (me?.is_admin && !isInsideTelegram()) {
    return <Layout />;
  }
  return <UserLayout />;
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />

          <Route
            path="/admin"
            element={
              <RequireAuth>
                <Layout />
              </RequireAuth>
            }
          >
            <Route index element={<Dashboard />} />
            <Route path="tickets" element={<Tickets />} />
          </Route>

          <Route
            path="/"
            element={
              <RequireAuth>
                <Root />
              </RequireAuth>
            }
          >
            <Route index element={<UserHome />} />
            <Route path="tickets" element={<MyTickets />} />
            <Route path="tickets/:ticketId" element={<TicketDetail />} />
            <Route path="new" element={<NewTicket />} />
            <Route path="settings" element={<UserSettings />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
