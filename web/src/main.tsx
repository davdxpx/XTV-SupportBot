import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import { BrowserRouter, Route, Routes, Navigate } from 'react-router-dom';

import '@/styles/theme.css';
import { AdminLayout } from '@/components/AdminLayout';
import { UserLayout } from '@/components/UserLayout';
import { Login } from '@/pages/Login';
import { Register } from '@/pages/Register';
import { UserHome } from '@/pages/user/Home';
import { NewTicket } from '@/pages/user/NewTicket';
import { MyTickets } from '@/pages/user/MyTickets';
import { TicketDetail } from '@/pages/user/TicketDetail';
import { UserSettings } from '@/pages/user/Settings';
import { Overview } from '@/pages/admin/Overview';
import { Inbox } from '@/pages/admin/Inbox';
import { AdminTicketDetail } from '@/pages/admin/AdminTicketDetail';
import { Projects } from '@/pages/admin/Projects';
import { ProjectDetail } from '@/pages/admin/ProjectDetail';
import { Rules } from '@/pages/admin/Rules';
import { Accounts } from '@/pages/admin/Accounts';
import { Access } from '@/pages/admin/Access';
import { ApiKeys } from '@/pages/admin/ApiKeys';
import { Content } from '@/pages/admin/Content';
import { Broadcasts } from '@/pages/admin/Broadcasts';
import { Account } from '@/pages/admin/Account';
import { Settings } from '@/pages/admin/Settings';
import { ApiError, getMe } from '@/lib/api';
import { bootTelegram, isInsideTelegram } from '@/lib/telegram';
import { bootTheme } from '@/lib/theme';

// Apply the saved theme before first paint to avoid a flash.
bootTheme();

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

  // Always attempt /me: the admin session lives in an httpOnly cookie the
  // SPA can't read, so we optimistically ask the server and let a 401
  // bounce us to /login (handled below).
  const me = useQuery({
    queryKey: ['me'],
    queryFn: getMe,
  });

  if (me.isLoading) {
    return (
      <div className="loading-screen">
        <div className="loading-screen-inner">
          <span className="spinner spinner-lg spinner-color" />
          <div className="loading-screen-msg">
            {inTelegram ? 'Signing you in…' : 'Loading…'}
          </div>
        </div>
      </div>
    );
  }

  if (me.isError) {
    const status = me.error instanceof ApiError ? me.error.status : 0;
    if (status === 401 || status === 422) return <Navigate to="/login" replace />;
    return (
      <div className="error-screen">
        <div style={{ textAlign: 'center', maxWidth: 360 }}>
          <div style={{ fontSize: 36, marginBottom: 8 }}>😶‍🌫️</div>
          <h2 style={{ margin: 0 }}>Couldn't reach the server</h2>
          <p className="muted">
            ({status || 'network'}) — try reloading.
          </p>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => window.location.reload()}
            style={{ marginTop: 12 }}
          >
            Reload
          </button>
        </div>
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
          <Route path="/register" element={<Register />} />

          <Route path="/admin" element={<AdminLayout />}>
            <Route index element={<Overview />} />
            <Route path="inbox" element={<Inbox />} />
            <Route path="tickets/:ticketId" element={<AdminTicketDetail />} />
            <Route path="projects" element={<Projects />} />
            <Route path="projects/:id" element={<ProjectDetail />} />
            <Route path="rules" element={<Rules />} />
            <Route path="accounts" element={<Accounts />} />
            <Route path="access" element={<Access />} />
            <Route path="keys" element={<ApiKeys />} />
            <Route path="content" element={<Content />} />
            <Route path="broadcasts" element={<Broadcasts />} />
            <Route path="account" element={<Account />} />
            <Route path="settings" element={<Settings />} />
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
