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
    { to: '/', label: 'Home', icon: '🏠', end: true },
    { to: '/tickets', label: 'Tickets', icon: '🗂' },
    { to: '/new', label: 'New', icon: '📮' },
    { to: '/settings', label: 'Settings', icon: '⚙️' },
  ];

  return (
    <div className="user-shell">
      <header className="user-header">
        <span className="user-brand">{me?.brand_name ?? 'Support'}</span>
        {me?.first_name && <span className="user-greet">· Hi {me.first_name}</span>}
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
