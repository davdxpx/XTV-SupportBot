import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { clearApiKey, getMe, logout as logoutApi, type MeResponse } from '@/lib/api';
import { getTgUser } from '@/lib/telegram';
import { getTheme, setTheme, type ThemePref } from '@/lib/theme';

function initials(me?: MeResponse): string {
  const first = me?.first_name?.trim() ?? '';
  const last = me?.last_name?.trim() ?? '';
  const a = first.charAt(0);
  const b = last.charAt(0) || first.charAt(1);
  return (a + b).toUpperCase() || '?';
}

/** Deterministic accent hue from the identity so avatars stay stable. */
function hue(seed: string): number {
  let h = 0;
  for (let i = 0; i < seed.length; i += 1) h = (h * 31 + seed.charCodeAt(i)) % 360;
  return h;
}

function Avatar({ me, size = 36 }: { me?: MeResponse; size?: number }) {
  const photo = getTgUser()?.photo_url;
  if (photo) {
    return <img className="avatar" src={photo} alt="" style={{ width: size, height: size }} />;
  }
  const seed = me?.username || me?.first_name || 'x';
  const h = hue(seed);
  if (me?.auth_method === 'apikey') {
    return (
      <span className="avatar avatar-key" style={{ width: size, height: size }} aria-hidden>
        <svg width={size * 0.5} height={size * 0.5} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square">
          <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3" />
        </svg>
      </span>
    );
  }
  return (
    <span
      className="avatar avatar-initials"
      style={{ width: size, height: size, background: `hsl(${h} 55% 32%)`, color: '#fff' }}
      aria-hidden
    >
      {initials(me)}
    </span>
  );
}

function roleLabel(me?: MeResponse): string {
  if (me?.auth_method === 'apikey') return 'API Key';
  if (me?.role) return me.role.toUpperCase();
  return me?.is_admin ? 'ADMIN' : 'AGENT';
}

function displayName(me?: MeResponse): string {
  if (me?.auth_method === 'apikey') return me.first_name || 'API Key';
  const n = [me?.first_name, me?.last_name].filter(Boolean).join(' ').trim();
  return n || me?.username || 'Account';
}

const THEMES: { value: ThemePref; label: string }[] = [
  { value: 'auto', label: 'AUTO' },
  { value: 'light', label: 'LIGHT' },
  { value: 'dark', label: 'DARK' },
];

export function ProfileMenu({ variant = 'sidebar' }: { variant?: 'sidebar' | 'bar' }) {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { data: me } = useQuery({ queryKey: ['me'], queryFn: getMe });
  const [open, setOpen] = useState(false);
  const [theme, setThemeState] = useState<ThemePref>(getTheme);
  const [loggingOut, setLoggingOut] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false);
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const pickTheme = (t: ThemePref) => {
    setTheme(t);
    setThemeState(t);
  };

  const logout = async () => {
    setLoggingOut(true);
    try {
      await logoutApi();
    } catch {
      // best-effort — clear locally regardless
    }
    clearApiKey();
    qc.clear();
    navigate('/login');
  };

  const go = (to: string) => {
    setOpen(false);
    navigate(to);
  };

  return (
    <div className={`profile ${variant === 'bar' ? 'profile-bar' : 'profile-side'}`} ref={ref}>
      {open && (
        <div className={`profile-menu pop-in ${variant === 'bar' ? 'profile-menu-bar' : ''}`} role="menu">
          <div className="profile-menu-head">
            <Avatar me={me} size={40} />
            <div className="profile-menu-id">
              <span className="profile-menu-name">{displayName(me)}</span>
              <span className="profile-menu-sub">
                {me?.username && me.auth_method !== 'apikey' ? `@${me.username} · ` : ''}
                {roleLabel(me)}
              </span>
            </div>
          </div>

          <div className="profile-menu-section">
            <span className="profile-menu-label">THEME</span>
            <div className="seg">
              {THEMES.map((t) => (
                <button
                  key={t.value}
                  type="button"
                  className={`seg-item${theme === t.value ? ' active' : ''}`}
                  onClick={() => pickTheme(t.value)}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          <div className="profile-menu-section">
            <button type="button" className="profile-menu-item" role="menuitem" onClick={() => go('/admin/account')}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></svg>
              <span>Account settings</span>
            </button>
          </div>

          {me?.is_admin && (
            <div className="profile-menu-section">
              <button type="button" className="profile-menu-item" role="menuitem" onClick={() => go('/admin/accounts')}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" /></svg>
                <span>Accounts</span>
              </button>
              <button type="button" className="profile-menu-item" role="menuitem" onClick={() => go('/admin/keys')}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3" /></svg>
                <span>API Keys</span>
              </button>
            </div>
          )}

          <div className="profile-menu-section">
            <button type="button" className="profile-menu-item danger" role="menuitem" disabled={loggingOut} onClick={logout}>
              {loggingOut ? <span className="spinner" style={{ width: 14, height: 14 }} /> : (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" /></svg>
              )}
              <span>Log out</span>
            </button>
          </div>
        </div>
      )}

      <button type="button" className="profile-trigger" onClick={() => setOpen((v) => !v)} aria-haspopup="menu" aria-expanded={open} title={displayName(me)}>
        <Avatar me={me} size={variant === 'bar' ? 28 : 34} />
        {variant === 'sidebar' ? (
          <span className="profile-trigger-id">
            <span className="profile-trigger-name">{displayName(me)}</span>
            <span className="profile-trigger-sub">{roleLabel(me)}</span>
          </span>
        ) : (
          <span className="profile-trigger-label">PROFILE</span>
        )}
      </button>
    </div>
  );
}
