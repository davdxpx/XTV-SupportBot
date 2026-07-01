import { useState, type ReactNode } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { ProfileMenu } from '@/components/ProfileMenu';

interface NavItem {
  to: string;
  label: string;
  icon: ReactNode;
  end?: boolean;
  primary?: boolean; // shown directly in the mobile bottom bar
}

const links: NavItem[] = [
  { to: '/admin', label: 'OVERVIEW', primary: true, end: true, icon: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square" className="icon"><rect x="3" y="3" width="18" height="18" rx="2" ry="2" /><line x1="3" y1="9" x2="21" y2="9" /><line x1="9" y1="21" x2="9" y2="9" /></svg>
  )},
  { to: '/admin/inbox', label: 'QUEUE', primary: true, icon: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square" className="icon"><polyline points="22 12 16 12 14 15 10 15 8 12 2 12" /><path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z" /></svg>
  )},
  { to: '/admin/projects', label: 'PROJECTS', primary: true, icon: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square" className="icon"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" /></svg>
  )},
  { to: '/admin/rules', label: 'RULES', icon: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square" className="icon"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" /></svg>
  )},
  { to: '/admin/accounts', label: 'ACCOUNTS', icon: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square" className="icon"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" /></svg>
  )},
  { to: '/admin/access', label: 'ACCESS', icon: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square" className="icon"><rect x="3" y="11" width="18" height="11" rx="2" ry="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /></svg>
  )},
  { to: '/admin/keys', label: 'KEYS', icon: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square" className="icon"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3" /></svg>
  )},
  { to: '/admin/content', label: 'CONTENT', icon: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square" className="icon"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" /><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" /></svg>
  )},
  { to: '/admin/broadcasts', label: 'BROADCAST', icon: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square" className="icon"><path d="M3 11l18-5v12L3 14v-3z" /><path d="M11.6 16.8a3 3 0 1 1-5.8-1.6" /></svg>
  )},
  { to: '/admin/settings', label: 'SETTINGS', icon: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square" className="icon"><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" /></svg>
  )},
];

export function AdminLayout() {
  const [menuOpen, setMenuOpen] = useState(false);
  const primary = links.filter((l) => l.primary);

  return (
    <div className="admin-shell">
      <aside className="admin-side">
        <div className="admin-brand">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--tg-accent)" strokeWidth="3" strokeLinecap="square">
            <line x1="4" y1="4" x2="20" y2="20" /><line x1="20" y1="4" x2="4" y2="20" />
          </svg>
          <span>XTV ADMIN</span>
        </div>
        <nav className="admin-nav">
          {links.map((s) => (
            <NavLink key={s.to} to={s.to} end={s.end} className={({ isActive }) => `admin-link${isActive ? ' active' : ''}`}>
              {s.icon}
              <span>{s.label}</span>
            </NavLink>
          ))}
        </nav>
        <ProfileMenu variant="sidebar" />
      </aside>

      <main className="admin-main">
        <Outlet />
      </main>

      {/* Mobile bottom bar */}
      <nav className="admin-bottombar">
        {primary.map((s) => (
          <NavLink key={s.to} to={s.to} end={s.end} className={({ isActive }) => `bottombar-item${isActive ? ' active' : ''}`}>
            <span className="bottombar-icon">{s.icon}</span>
            <span>{s.label}</span>
          </NavLink>
        ))}
        <button type="button" className="bottombar-item" onClick={() => setMenuOpen(true)} aria-haspopup="dialog">
          <span className="bottombar-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square"><line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="18" x2="21" y2="18" /></svg>
          </span>
          <span>MENU</span>
        </button>
        <ProfileMenu variant="bar" />
      </nav>

      {menuOpen && (
        <div className="modal-backdrop" onClick={() => setMenuOpen(false)}>
          <div className="nav-sheet pop-in" onClick={(e) => e.stopPropagation()} role="dialog" aria-label="Navigation">
            <div className="nav-sheet-head">
              <span className="section-title" style={{ margin: 0 }}>NAVIGATE</span>
              <button type="button" className="btn-icon" onClick={() => setMenuOpen(false)} aria-label="Close">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
              </button>
            </div>
            <div className="nav-sheet-grid">
              {links.map((s) => (
                <NavLink key={s.to} to={s.to} end={s.end} onClick={() => setMenuOpen(false)} className={({ isActive }) => `nav-sheet-item${isActive ? ' active' : ''}`}>
                  {s.icon}
                  <span>{s.label}</span>
                </NavLink>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
