import { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { ApiError, login as loginApi, setApiKey } from '@/lib/api';
import { isInsideTelegram } from '@/lib/telegram';

/**
 * Login screen — admin-only.
 *
 * Primary: real username/password account (server-side session cookie).
 * Secondary (demoted, still supported): paste a legacy API key.
 * Auto-bounces to ``/`` inside Telegram, where ``initData`` covers auth.
 */
export function Login() {
  const navigate = useNavigate();
  const qc = useQueryClient();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [showKey, setShowKey] = useState(false);
  const [keyValue, setKeyValue] = useState('');
  const [keyBusy, setKeyBusy] = useState(false);

  useEffect(() => {
    if (isInsideTelegram()) navigate('/', { replace: true });
  }, [navigate]);

  if (isInsideTelegram()) {
    return (
      <div className="loading-screen">
        <div className="loading-screen-inner">
          <span className="spinner spinner-lg spinner-color" />
          <div className="loading-screen-msg">Signing you in…</div>
        </div>
      </div>
    );
  }

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password || busy) return;
    setBusy(true);
    setError(null);
    try {
      await loginApi(username.trim(), password);
      await qc.invalidateQueries({ queryKey: ['me'] });
      navigate('/', { replace: true });
    } catch (err) {
      const status = err instanceof ApiError ? err.status : 0;
      setError(
        status === 429
          ? 'Too many attempts — wait a few minutes and try again.'
          : 'Invalid username or password.',
      );
      setBusy(false);
    }
  };

  const onKeySubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = keyValue.trim();
    if (!trimmed || keyBusy) return;
    setKeyBusy(true);
    setApiKey(trimmed);
    setTimeout(() => navigate('/', { replace: true }), 80);
  };

  return (
    <div className="login-shell">
      <form className="login-card stack" onSubmit={onSubmit} style={{ gap: 24, padding: 32 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <div className="login-brand" style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--tg-accent)" strokeWidth="3" strokeLinecap="square">
              <line x1="4" y1="4" x2="20" y2="20"></line>
              <line x1="20" y1="4" x2="4" y2="20"></line>
            </svg>
            <span>XTV-SupportBot</span>
          </div>
          <div className="login-sub" style={{ textTransform: 'uppercase' }}>Admin Console</div>
        </div>

        <div className="stack" style={{ gap: 8 }}>
          <label className="label" htmlFor="login-username">USERNAME</label>
          <input
            id="login-username"
            type="text"
            className="input"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="username"
            autoFocus
            autoComplete="username"
          />
        </div>

        <div className="stack" style={{ gap: 8 }}>
          <label className="label" htmlFor="login-password">PASSWORD</label>
          <input
            id="login-password"
            type="password"
            className="input"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••••"
            autoComplete="current-password"
          />
        </div>

        {error && (
          <div style={{ padding: 12, border: '1px solid var(--tg-danger)', background: 'var(--tg-danger-soft)', color: 'var(--tg-text)', fontSize: 13, fontFamily: 'IBM Plex Mono, monospace' }}>
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={!username.trim() || !password || busy}
          className="btn btn-primary"
          style={{ width: '100%', padding: '14px', fontSize: 15 }}
        >
          {busy && <span className="spinner" />}
          {busy ? 'SIGNING IN...' : 'SIGN IN'}
        </button>

        <p style={{ fontSize: 12, textAlign: 'center', margin: 0, color: 'var(--tg-text-dim)' }}>
          Have an invite key from your admin?{' '}
          <Link to="/register" style={{ color: 'var(--tg-accent)' }}>Create your account</Link>
        </p>

        <div style={{ borderTop: '1px solid var(--tg-border)', paddingTop: 16, textAlign: 'center' }}>
          {!showKey ? (
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => setShowKey(true)}
              style={{ fontSize: 12 }}
            >
              Log in with an API key instead
            </button>
          ) : (
            <div className="stack" style={{ gap: 8 }} onSubmit={onKeySubmit}>
              <label className="label" htmlFor="api-key-input" style={{ textAlign: 'left' }}>
                API KEY CREDENTIAL
              </label>
              <input
                id="api-key-input"
                type="password"
                className="input"
                value={keyValue}
                onChange={(e) => setKeyValue(e.target.value)}
                placeholder="xtv_..."
                autoComplete="off"
              />
              <button
                type="button"
                onClick={onKeySubmit}
                disabled={!keyValue.trim() || keyBusy}
                className="btn btn-ghost"
                style={{ width: '100%', padding: '12px' }}
              >
                {keyBusy && <span className="spinner" />}
                {keyBusy ? 'AUTHENTICATING...' : 'USE API KEY'}
              </button>
            </div>
          )}
        </div>
      </form>
    </div>
  );
}
