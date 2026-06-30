import { NavLink, Outlet } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useEffect } from 'react';
import { getMe } from '@/lib/api';
import { getWebApp } from '@/lib/telegram';

/**
 * Bottom-tab-bar layout for the Mini-App. When opened inside Telegram,
 * the SDK's theme params are mirrored onto the :root CSS variables so
 * the whole SPA follows the user's client theme automatically. In a
 * regular browser we fall through to the prefers-color-scheme defaults.
 */
export function UserLayout() {
  const { data: me } = useQuery({ queryKey: ['me'], queryFn: getMe });

  useEffect(() => {
    const tg = getWebApp();
    const theme = tg?.themeParams;
    if (!theme || Object.keys(theme).length === 0) return;
    const root = document.documentElement;
    const map: Record<string, string> = {
      bg_color: '--tg-bg',
      secondary_bg_color: '--tg-surface',
      section_bg_color: '--tg-surface-hi',
      text_color: '--tg-text',
      hint_color: '--tg-text-dim',
      button_color: '--tg-accent',
      button_text_color: '--tg-accent-text',
    };
    for (const [tgKey, cssVar] of Object.entries(map)) {
      const value = theme[tgKey];
      if (value) root.style.setProperty(cssVar, value);
    }
  }, []);

  const tabs = [
    { to: '/', label: 'HOME', icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square">
        <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
        <polyline points="9 22 9 12 15 12 15 22"></polyline>
      </svg>
    ), end: true },
    { to: '/tickets', label: 'TICKETS', icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square">
        <line x1="8" y1="6" x2="21" y2="6"></line>
        <line x1="8" y1="12" x2="21" y2="12"></line>
        <line x1="8" y1="18" x2="21" y2="18"></line>
        <line x1="3" y1="6" x2="3.01" y2="6"></line>
        <line x1="3" y1="12" x2="3.01" y2="12"></line>
        <line x1="3" y1="18" x2="3.01" y2="18"></line>
      </svg>
    )},
    { to: '/new', label: 'NEW', icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square">
        <line x1="12" y1="5" x2="12" y2="19"></line>
        <line x1="5" y1="12" x2="19" y2="12"></line>
      </svg>
    )},
    { to: '/settings', label: 'CONFIG', icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square">
        <circle cx="12" cy="12" r="3"></circle>
        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
      </svg>
    )},
  ];

  return (
    <div className="user-shell">
      <header className="user-header">
        <span className="user-brand">{me?.brand_name ?? 'SUPPORT'}</span>
        {me?.first_name && <span className="user-greet">// {me.first_name}</span>}
      </header>

      <main className="user-main">
        <Outlet />
      </main>

      <nav className="tabbar">
        {tabs.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            end={tab.end}
            className={({ isActive }) => `tabbar-item${isActive ? ' active' : ''}`}
          >
            <div className="tabbar-icon">{tab.icon}</div>
            <div>{tab.label}</div>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
