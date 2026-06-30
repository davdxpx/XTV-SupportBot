import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { clearApiKey } from '@/lib/api';

export function AdminLayout() {
  const navigate = useNavigate();
  const logout = () => {
    clearApiKey();
    navigate('/login');
  };

  const links = [
    { to: '/admin', label: 'OVERVIEW', icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square" className="icon">
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
        <line x1="3" y1="9" x2="21" y2="9"></line>
        <line x1="9" y1="21" x2="9" y2="9"></line>
      </svg>
    ), end: true },
    { to: '/admin/inbox', label: 'QUEUE', icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square" className="icon">
        <polyline points="22 12 16 12 14 15 10 15 8 12 2 12"></polyline>
        <path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"></path>
      </svg>
    )},
    { to: '/admin/projects', label: 'PROJECTS', icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square" className="icon">
        <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
      </svg>
    )},
    { to: '/admin/rules', label: 'RULES', icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square" className="icon">
        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
      </svg>
    )},
  ];

  return (
    <div className="admin-shell">
      <aside className="admin-side">
        <div className="admin-brand">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--tg-accent)" strokeWidth="3" strokeLinecap="square">
            <line x1="4" y1="4" x2="20" y2="20"></line>
            <line x1="20" y1="4" x2="4" y2="20"></line>
          </svg>
          <span>XTV ADMIN</span>
        </div>
        {links.map((s) => (
          <NavLink
            key={s.to}
            to={s.to}
            end={s.end}
            className={({ isActive }) => `admin-link${isActive ? ' active' : ''}`}
          >
            {s.icon}
            <span>{s.label}</span>
          </NavLink>
        ))}
        <div style={{ marginTop: 'auto', paddingTop: 16 }}>
          <button type="button" onClick={logout} className="btn btn-ghost" style={{ width: '100%', padding: '10px' }} title="Log out">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square" className="icon">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
              <polyline points="16 17 21 12 16 7"></polyline>
              <line x1="21" y1="12" x2="9" y2="12"></line>
            </svg>
            <span style={{ marginLeft: 8 }}>DISCONNECT</span>
          </button>
        </div>
      </aside>
      <main className="admin-main">
        <Outlet />
      </main>
    </div>
  );
}
