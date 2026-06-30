import { useState, type CSSProperties } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { changePassword, getMe } from '@/lib/api';
import { getTheme, setTheme, type ThemePref } from '@/lib/theme';

const THEMES: { value: ThemePref; label: string }[] = [
  { value: 'auto', label: 'AUTO' },
  { value: 'light', label: 'LIGHT' },
  { value: 'dark', label: 'DARK' },
];

const card: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 12,
  border: '1px solid var(--tg-border)',
  padding: 20,
};
const dim: CSSProperties = { color: 'var(--tg-text-dim)' };
const mono: CSSProperties = { fontFamily: 'IBM Plex Mono, monospace' };

function pwError(err: unknown): string {
  const s = String(err);
  if (s.includes('wrong_password')) return 'Current password is incorrect.';
  if (s.includes('weak_password')) return 'New password is too weak (min 10 chars, not your username).';
  if (s.includes('password_unchanged')) return 'New password must differ from the current one.';
  if (s.includes('not_an_account')) return 'Password change is only available for account logins.';
  return 'Could not change password.';
}

export function Account() {
  const { data: me } = useQuery({ queryKey: ['me'], queryFn: getMe });
  const [theme, setThemeState] = useState<ThemePref>(getTheme);
  const [cur, setCur] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');

  const pickTheme = (t: ThemePref) => {
    setTheme(t);
    setThemeState(t);
  };

  const change = useMutation({
    mutationFn: () => changePassword(cur, next),
    onSuccess: () => {
      setCur('');
      setNext('');
      setConfirm('');
    },
  });

  const isAccount = me?.auth_method === 'account';
  const mismatch = confirm.length > 0 && next !== confirm;
  const canSubmit = isAccount && cur.length > 0 && next.length >= 10 && next === confirm && !change.isPending;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24, maxWidth: 560 }}>
      <h1 className="heading">ACCOUNT</h1>

      <section style={card}>
        <span className="section-title" style={{ margin: 0 }}>IDENTITY</span>
        <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '8px 16px', fontSize: 14 }}>
          <span style={dim}>Name</span>
          <span>{[me?.first_name, me?.last_name].filter(Boolean).join(' ') || '—'}</span>
          {me?.username && <><span style={dim}>Username</span><span>@{me.username}</span></>}
          <span style={dim}>Role</span>
          <span style={{ ...mono, textTransform: 'uppercase' }}>{me?.role || (me?.is_admin ? 'admin' : 'agent')}</span>
          <span style={dim}>Sign-in</span>
          <span style={mono}>{me?.auth_method ?? '—'}</span>
        </div>
      </section>

      <section style={card}>
        <span className="section-title" style={{ margin: 0 }}>APPEARANCE</span>
        <div className="seg">
          {THEMES.map((t) => (
            <button key={t.value} type="button" className={`seg-item${theme === t.value ? ' active' : ''}`} onClick={() => pickTheme(t.value)}>
              {t.label}
            </button>
          ))}
        </div>
      </section>

      <section style={card}>
        <span className="section-title" style={{ margin: 0 }}>CHANGE PASSWORD</span>
        {!isAccount ? (
          <p style={{ ...dim, margin: 0, fontSize: 13 }}>
            Password change is only available for username/password logins, not API-key or Telegram sessions.
          </p>
        ) : (
          <form
            style={{ display: 'flex', flexDirection: 'column', gap: 12 }}
            onSubmit={(e) => { e.preventDefault(); if (canSubmit) change.mutate(); }}
          >
            <input className="input" type="password" autoComplete="current-password" placeholder="Current password"
              value={cur} onChange={(e) => setCur(e.target.value)} />
            <input className="input" type="password" autoComplete="new-password" placeholder="New password (min 10 chars)"
              value={next} onChange={(e) => setNext(e.target.value)} />
            <input className="input" type="password" autoComplete="new-password" placeholder="Confirm new password"
              value={confirm} onChange={(e) => setConfirm(e.target.value)} />
            {mismatch && <span style={{ color: 'var(--tg-danger)', fontSize: 12 }}>Passwords don't match.</span>}
            {change.isError && <span style={{ color: 'var(--tg-danger)', fontSize: 12 }}>{pwError(change.error)}</span>}
            {change.isSuccess && <span style={{ color: 'var(--tg-success)', fontSize: 12 }}>Password updated. Other sessions were signed out.</span>}
            <button type="submit" className="btn btn-primary btn-sm" disabled={!canSubmit} style={{ alignSelf: 'flex-start' }}>
              {change.isPending ? 'SAVING…' : 'UPDATE PASSWORD'}
            </button>
          </form>
        )}
      </section>
    </div>
  );
}
