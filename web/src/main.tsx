import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import { BrowserRouter, Route, Routes, Navigate } from 'react-router-dom';

import { AdminLayout } from '@/components/AdminLayout';
import { UserLayout } from '@/components/UserLayout';
import { Login } from '@/pages/Login';
import { UserHome } from '@/pages/user/Home';
import { NewTicket } from '@/pages/user/NewTicket';
import { MyTickets } from '@/pages/user/MyTickets';
import { TicketDetail } from '@/pages/user/TicketDetail';
import { UserSettings } from '@/pages/user/Settings';
import { Overview } from '@/pages/admin/Overview';
import { Inbox } from '@/pages/admin/Inbox';
import { AdminTicketDetail } from '@/pages/admin/AdminTicketDetail';
import { Projects } from '@/pages/admin/Projects';
import { Rules } from '@/pages/admin/Rules';
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
 * Root switcher — asks /api/v1/me once, then picks the right shell:
 *  - Desktop browser + admin key → AdminLayout (full dashboard)
 *  - Every Telegram user (admin or not) → UserLayout (Mini-App UX)
 *  - Telegram admins who want the power UI go to /admin/* explicitly
 */
function Root() {
  const { data: me, isLoading } = useQuery({ queryKey: ['me'], queryFn: getMe });
  if (isLoading) return <div style={{ padding: 40 }}>Loading…</div>;
  if (me?.is_admin && !isInsideTelegram()) {
    return <AdminLayout />;
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
                <AdminLayout />
              </RequireAuth>
            }
          >
            <Route index element={<Overview />} />
            <Route path="inbox" element={<Inbox />} />
            <Route path="tickets/:ticketId" element={<AdminTicketDetail />} />
            <Route path="projects" element={<Projects />} />
            <Route path="rules" element={<Rules />} />
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
