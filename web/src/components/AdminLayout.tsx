import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { clearApiKey } from '@/lib/api';

export function AdminLayout() {
  const navigate = useNavigate();
  const logout = () => {
    clearApiKey();
    navigate('/login');
  };

  const links = [
    { to: '/admin', label: 'Overview', icon: '📊', end: true },
    { to: '/admin/inbox', label: 'Inbox', icon: '🗂' },
    { to: '/admin/projects', label: 'Projects', icon: '📁' },
    { to: '/admin/rules', label: 'Rules', icon: '⚙️' },
  ];

  return (
    <div className="admin-shell">
      <aside className="admin-side">
        <div className="admin-brand">XTV Admin</div>
        {links.map((s) => (
          <NavLink
            key={s.to}
            to={s.to}
            end={s.end}
            className={({ isActive }) => `admin-link${isActive ? ' active' : ''}`}
          >
            <span>{s.icon}</span>
            <span>{s.label}</span>
          </NavLink>
        ))}
        <div style={{ marginTop: 'auto', paddingTop: 16 }}>
          <button type="button" onClick={logout} className="btn btn-ghost" style={{ width: '100%' }}>
            Sign out
          </button>
        </div>
      </aside>
      <main className="admin-main">
        <Outlet />
      </main>
    </div>
  );
}
