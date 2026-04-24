import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { setApiKey } from '@/lib/api';
import { isInsideTelegram } from '@/lib/telegram';

/**
 * Login screen.
 *
 * Two modes, picked automatically:
 *
 *  1. Inside Telegram Mini-App — we already have ``initData``; skip
 *     the form entirely and bounce to ``/`` so the SPA shows the
 *     user home / admin dashboard (RequireAuth + ``/api/v1/me``
 *     handle the rest).
 *
 *  2. Regular browser — ask the admin for their API key, persist
 *     it in localStorage, then bounce to ``/``.
 */
export function Login() {
  const [value, setValue] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    if (isInsideTelegram()) navigate('/', { replace: true });
  }, [navigate]);

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!value.trim()) return;
    setApiKey(value.trim());
    navigate('/', { replace: true });
  };

  if (isInsideTelegram()) {
    return <p style={{ padding: 24 }}>Signing you in…</p>;
  }

  return (
    <div
      style={{
        maxWidth: 420,
        margin: '10vh auto',
        padding: 20,
        fontFamily: 'system-ui, sans-serif',
      }}
    >
      <h1 style={{ marginTop: 0 }}>XTV-SupportBot</h1>
      <p>Paste your API key to continue.</p>
      <form onSubmit={onSubmit}>
        <input
          type="password"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="xtv_…"
          style={{
            width: '100%',
            padding: 10,
            fontSize: 15,
            borderRadius: 8,
            border: '1px solid #cbd5e1',
          }}
          autoFocus
        />
        <button
          type="submit"
          disabled={!value.trim()}
          style={{
            marginTop: 12,
            padding: '10px 18px',
            borderRadius: 8,
            border: 'none',
            background: value.trim() ? '#2563eb' : '#cbd5e1',
            color: '#fff',
            cursor: value.trim() ? 'pointer' : 'not-allowed',
          }}
        >
          Sign in
        </button>
      </form>
      <p style={{ marginTop: 16, color: '#6b7280', fontSize: 13 }}>
        Generate a key in the bot with <code>/apikey create admin:full</code>.
      </p>
    </div>
  );
}
