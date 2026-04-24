import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { clearApiKey } from '@/lib/api';

/**
 * Full-width admin console layout — left rail with section links,
 * top bar with logout. Used by the desktop browser admin flow.
 * Telegram admins can also reach this at ``/admin/*`` if they want
 * the power-user view instead of the Mini-App UX.
 */
export function AdminLayout() {
  const navigate = useNavigate();
  const logout = () => {
    clearApiKey();
    navigate('/login');
  };

  const sections: Array<{ to: string; label: string; icon: string; end?: boolean }> = [
    { to: '/admin', label: 'Overview', icon: '📊', end: true },
    { to: '/admin/inbox', label: 'Inbox', icon: '🗂' },
    { to: '/admin/projects', label: 'Projects', icon: '📁' },
    { to: '/admin/rules', label: 'Rules', icon: '⚙️' },
  ];

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: '220px 1fr',
        minHeight: '100vh',
        fontFamily: 'system-ui, sans-serif',
      }}
    >
      <aside
        style={{
          borderRight: '1px solid #e5e7eb',
          padding: 16,
          display: 'flex',
          flexDirection: 'column',
          gap: 8,
          background: '#f9fafb',
        }}
      >
        <div style={{ fontWeight: 700, fontSize: 16, padding: '4px 0 12px' }}>
          XTV Admin
        </div>
        {sections.map((s) => (
          <NavLink
            key={s.to}
            to={s.to}
            end={s.end}
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              padding: '10px 12px',
              borderRadius: 8,
              textDecoration: 'none',
              color: isActive ? '#ffffff' : '#111827',
              background: isActive ? '#2563eb' : 'transparent',
            })}
          >
            <span>{s.icon}</span>
            <span>{s.label}</span>
          </NavLink>
        ))}
        <div style={{ marginTop: 'auto', paddingTop: 16 }}>
          <button
            type="button"
            onClick={logout}
            style={{
              width: '100%',
              padding: '8px 12px',
              border: '1px solid #e5e7eb',
              background: 'transparent',
              borderRadius: 8,
              cursor: 'pointer',
            }}
          >
            Sign out
          </button>
        </div>
      </aside>
      <main style={{ padding: 24, overflowY: 'auto' }}>
        <Outlet />
      </main>
    </div>
  );
}
