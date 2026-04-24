import { NavLink, Outlet } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getMe } from '@/lib/api';
import { getWebApp } from '@/lib/telegram';

/**
 * Bottom-tab-bar layout used by every end-user page. Respects
 * Telegram's theme params when opened inside a Mini-App; falls back
 * to a neutral light theme in a regular browser.
 */
export function UserLayout() {
  const { data: me } = useQuery({ queryKey: ['me'], queryFn: getMe });
  const tg = getWebApp();
  const theme = tg?.themeParams ?? {};
  const bg = theme.bg_color ?? '#ffffff';
  const fg = theme.text_color ?? '#111827';
  const hint = theme.hint_color ?? '#6b7280';
  const accent = theme.button_color ?? '#2563eb';
  const activeFg = theme.button_text_color ?? '#ffffff';

  return (
    <div
      style={{
        minHeight: '100vh',
        background: bg,
        color: fg,
        display: 'flex',
        flexDirection: 'column',
        fontFamily:
          'system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
      }}
    >
      <header
        style={{
          padding: '12px 16px',
          borderBottom: `1px solid ${hint}33`,
          display: 'flex',
          alignItems: 'center',
          gap: 12,
        }}
      >
        <strong style={{ fontSize: 16 }}>
          {me?.brand_name ?? 'Support'}
        </strong>
        {me?.first_name && (
          <span style={{ color: hint, fontSize: 13 }}>
            · Hi {me.first_name}
          </span>
        )}
      </header>

      <main style={{ flex: 1, padding: 16, paddingBottom: 80 }}>
        <Outlet />
      </main>

      <nav
        style={{
          position: 'sticky',
          bottom: 0,
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          background: bg,
          borderTop: `1px solid ${hint}33`,
          paddingBottom: 'env(safe-area-inset-bottom)',
        }}
      >
        {[
          { to: '/', label: 'Home', icon: '🏠', end: true },
          { to: '/tickets', label: 'Tickets', icon: '🗂' },
          { to: '/new', label: 'New', icon: '📮' },
          { to: '/settings', label: 'Settings', icon: '⚙️' },
        ].map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            end={tab.end}
            style={({ isActive }) => ({
              padding: '10px 4px',
              textAlign: 'center',
              textDecoration: 'none',
              fontSize: 12,
              color: isActive ? activeFg : fg,
              background: isActive ? accent : 'transparent',
              borderRadius: isActive ? 10 : 0,
              margin: 4,
            })}
          >
            <div style={{ fontSize: 20 }}>{tab.icon}</div>
            <div>{tab.label}</div>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
