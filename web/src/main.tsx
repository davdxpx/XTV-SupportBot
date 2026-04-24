import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import { BrowserRouter, Route, Routes, Navigate } from 'react-router-dom';

import '@/styles/theme.css';
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
import { ApiError, getMe, hasCredentials } from '@/lib/api';
import { bootTelegram, isInsideTelegram } from '@/lib/telegram';

// Tell Telegram we're ready + expand the viewport so the Mini-App
// renders full-height. No-op outside Telegram.
bootTelegram();

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 10_000,
      refetchOnWindowFocus: false,
      retry: false,
    },
  },
});

/**
 * Root guard — decides which shell to render based on /api/v1/me.
 *
 *   inside Telegram (any user)         → UserLayout  (Mini-App UX)
 *   desktop browser + admin key + ok   → AdminLayout (full dashboard)
 *   no credentials / 401 / 422         → Login
 */
function Root() {
  const inTelegram = isInsideTelegram();
  const hasKey = !!hasCredentials();

  const me = useQuery({
    queryKey: ['me'],
    queryFn: getMe,
    enabled: inTelegram || hasKey,
  });

  if (!inTelegram && !hasKey) return <Navigate to="/login" replace />;

  if (me.isLoading) {
    return (
      <div style={{ padding: 40, textAlign: 'center', fontFamily: 'system-ui' }}>
        <div style={{ fontSize: 32, marginBottom: 8 }}>⏳</div>
        Loading…
      </div>
    );
  }

  if (me.isError) {
    // 401 from a bad key → clear it & bounce to login. Other errors → surface.
    const status = me.error instanceof ApiError ? me.error.status : 0;
    if (status === 401 || status === 422) return <Navigate to="/login" replace />;
    return (
      <div
        style={{
          padding: 40,
          textAlign: 'center',
          fontFamily: 'system-ui',
          color: '#991b1b',
        }}
      >
        Couldn't reach the server ({status || 'network'}). Try reloading.
      </div>
    );
  }

  if (me.data?.is_admin && !inTelegram) {
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

          <Route path="/admin" element={<AdminLayout />}>
            <Route index element={<Overview />} />
            <Route path="inbox" element={<Inbox />} />
            <Route path="tickets/:ticketId" element={<AdminTicketDetail />} />
            <Route path="projects" element={<Projects />} />
            <Route path="rules" element={<Rules />} />
          </Route>

          <Route path="/" element={<Root />}>
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
