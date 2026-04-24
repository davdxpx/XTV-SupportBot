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
      <form className="login-card stack" onSubmit={onSubmit}>
        <div className="login-brand">XTV-SupportBot</div>
        <div className="login-sub">Admin console</div>

        <label className="label" htmlFor="api-key-input">
          API key
        </label>
        <input
          id="api-key-input"
          type="password"
          className="input"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="xtv_…"
          autoFocus
          autoComplete="off"
        />
        <button
          type="submit"
          disabled={!value.trim() || busy}
          className="btn btn-primary"
        >
          {busy && <span className="spinner" />}
          {busy ? 'Signing in…' : 'Sign in'}
        </button>

        <p className="muted" style={{ fontSize: 13, textAlign: 'center', margin: 0 }}>
          Generate a key in the bot with <code>/apikey create admin:full</code>.
        </p>
      </form>
    </div>
  );
}
