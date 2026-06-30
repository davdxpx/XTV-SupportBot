import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { setApiKey } from '@/lib/api';
import { isInsideTelegram } from '@/lib/telegram';

/**
 * Login screen — admin-only.
 *
 * Auto-bounces to ``/`` when opened inside Telegram, since ``initData``
 * already covers auth. Only desktop browser admins without a stored
 * API key should ever see this form.
 */
export function Login() {
  const [value, setValue] = useState('');
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

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

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || busy) return;
    setBusy(true);
    setApiKey(trimmed);
    // Tiny delay so the spinner is perceptible — pure UX,
    // localStorage write is sync.
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
          <label className="label" htmlFor="api-key-input">
            API KEY CREDENTIAL
          </label>
          <input
            id="api-key-input"
            type="password"
            className="input"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="xtv_..."
            autoFocus
            autoComplete="off"
          />
        </div>
        <button
          type="submit"
          disabled={!value.trim() || busy}
          className="btn btn-primary"
          style={{ width: '100%', padding: '14px', fontSize: 15 }}
        >
          {busy && <span className="spinner" />}
          {busy ? 'AUTHENTICATING...' : 'AUTHENTICATE'}
        </button>

        <p style={{ fontSize: 12, textAlign: 'center', margin: 0, color: 'var(--tg-text-dim)', fontFamily: 'IBM Plex Mono, monospace' }}>
          GENERATE KEY: <code>/apikey create admin:full</code>
        </p>
      </form>
    </div>
  );
}
