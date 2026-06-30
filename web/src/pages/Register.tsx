import { useEffect, useRef, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { ApiError, checkUsername, register as registerApi } from '@/lib/api';
import { isInsideTelegram } from '@/lib/telegram';

// Mirror the server's rules EXACTLY (api/routes/auth.py).
const USERNAME_RE = /^[a-zA-Z][a-zA-Z0-9_]*$/;
const PASSWORD_MIN = 10;

type Avail = { state: 'idle' | 'checking' | 'ok' | 'taken' | 'invalid' };

export function Register() {
  const navigate = useNavigate();
  const qc = useQueryClient();

  const [username, setUsername] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [apiKey, setApiKey] = useState('');

  const [avail, setAvail] = useState<Avail>({ state: 'idle' });
  const [busy, setBusy] = useState(false);
  const [fieldError, setFieldError] = useState<{ field: string; msg: string } | null>(null);

  useEffect(() => {
    if (isInsideTelegram()) navigate('/', { replace: true });
  }, [navigate]);

  // Debounced live username availability with in-flight cancellation.
  const abortRef = useRef<AbortController | null>(null);
  useEffect(() => {
    const u = username.trim();
    if (!u) {
      setAvail({ state: 'idle' });
      return;
    }
    if (u.length < 3 || u.length > 32 || !USERNAME_RE.test(u)) {
      setAvail({ state: 'invalid' });
      return;
    }
    setAvail({ state: 'checking' });
    const t = setTimeout(async () => {
      abortRef.current?.abort();
      const ctrl = new AbortController();
      abortRef.current = ctrl;
      try {
        const res = await checkUsername(u, ctrl.signal);
        if (ctrl.signal.aborted) return;
        setAvail({ state: res.available ? 'ok' : res.reason === 'taken' ? 'taken' : 'invalid' });
      } catch {
        // network/abort — leave as checking; submit will surface real errors
      }
    }, 400);
    return () => clearTimeout(t);
  }, [username]);

  const passwordOk = password.length >= PASSWORD_MIN && password.toLowerCase() !== username.trim().toLowerCase();
  const confirmOk = confirm === password;
  const canSubmit =
    avail.state === 'ok' && !!firstName.trim() && passwordOk && confirmOk && !!apiKey.trim() && !busy;

  const ERROR_MAP: Record<string, { field: string; msg: string }> = {
    invalid_username_format: { field: 'username', msg: 'Username must be 3–32 chars, start with a letter, letters/numbers/underscore only.' },
    username_taken: { field: 'username', msg: 'That username is already taken.' },
    invalid_first_name: { field: 'firstName', msg: 'Please enter a first name (max 64 characters).' },
    weak_password: { field: 'password', msg: `Password must be at least ${PASSWORD_MIN} characters and not match your username.` },
    invalid_api_key_format: { field: 'apiKey', msg: "That doesn't look like an invite key." },
    invalid_or_used_registration_key: { field: 'apiKey', msg: "This invite key isn't valid or has already been used — ask whoever invited you for a new one." },
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    setBusy(true);
    setFieldError(null);
    try {
      await registerApi({
        username: username.trim(),
        first_name: firstName.trim(),
        last_name: lastName.trim() || null,
        password,
        api_key: apiKey.trim(),
      });
      await qc.invalidateQueries({ queryKey: ['me'] });
      navigate('/', { replace: true });
    } catch (err) {
      const code = err instanceof ApiError ? (err.body as { detail?: string })?.detail : undefined;
      setFieldError((code && ERROR_MAP[code]) || { field: '', msg: 'Registration failed — please try again.' });
      setBusy(false);
    }
  };

  const fe = (field: string) => (fieldError?.field === field ? fieldError.msg : null);

  return (
    <div className="login-shell">
      <form className="login-card stack" onSubmit={onSubmit} style={{ gap: 20, padding: 32 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <div className="login-brand" style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--tg-accent)" strokeWidth="3" strokeLinecap="square">
              <line x1="4" y1="4" x2="20" y2="20"></line>
              <line x1="20" y1="4" x2="4" y2="20"></line>
            </svg>
            <span>XTV-SupportBot</span>
          </div>
          <div className="login-sub" style={{ textTransform: 'uppercase' }}>Create your account</div>
        </div>

        <Field label="USERNAME" error={fe('username')} hint={availHint(avail)}>
          <input className="input" type="text" value={username} autoFocus autoComplete="username"
            onChange={(e) => setUsername(e.target.value)} placeholder="username" />
        </Field>

        <Field label="FIRST NAME" error={fe('firstName')}>
          <input className="input" type="text" value={firstName} autoComplete="given-name"
            onChange={(e) => setFirstName(e.target.value)} placeholder="First name" />
        </Field>

        <Field label="LAST NAME (OPTIONAL)">
          <input className="input" type="text" value={lastName} autoComplete="family-name"
            onChange={(e) => setLastName(e.target.value)} placeholder="Last name" />
        </Field>

        <Field label="PASSWORD" error={fe('password')}
          hint={password && !passwordOk ? { tone: 'dim', text: `At least ${PASSWORD_MIN} characters, not your username.` } : undefined}>
          <input className="input" type="password" value={password} autoComplete="new-password"
            onChange={(e) => setPassword(e.target.value)} placeholder="••••••••••" />
        </Field>

        <Field label="CONFIRM PASSWORD"
          hint={confirm && !confirmOk ? { tone: 'bad', text: "Passwords don't match." } : undefined}>
          <input className="input" type="password" value={confirm} autoComplete="new-password"
            onChange={(e) => setConfirm(e.target.value)} placeholder="••••••••••" />
        </Field>

        <Field label="INVITE KEY" error={fe('apiKey')}>
          <input className="input" type="password" value={apiKey} autoComplete="off"
            onChange={(e) => setApiKey(e.target.value)} placeholder="xtv_..." />
        </Field>

        {fieldError && !fieldError.field && (
          <div style={{ padding: 12, border: '1px solid var(--tg-danger)', background: 'var(--tg-danger-soft)', color: 'var(--tg-text)', fontSize: 13, fontFamily: 'IBM Plex Mono, monospace' }}>
            {fieldError.msg}
          </div>
        )}

        <button type="submit" disabled={!canSubmit} className="btn btn-primary"
          style={{ width: '100%', padding: '14px', fontSize: 15 }}>
          {busy && <span className="spinner" />}
          {busy ? 'CREATING...' : 'CREATE ACCOUNT'}
        </button>

        <p style={{ fontSize: 12, textAlign: 'center', margin: 0, color: 'var(--tg-text-dim)' }}>
          Already have an account?{' '}
          <Link to="/login" style={{ color: 'var(--tg-accent)' }}>Sign in</Link>
        </p>
      </form>
    </div>
  );
}

type Hint = { tone: 'ok' | 'bad' | 'dim'; text: string };

function availHint(a: Avail): Hint | undefined {
  if (a.state === 'checking') return { tone: 'dim', text: 'Checking…' };
  if (a.state === 'ok') return { tone: 'ok', text: 'Available' };
  if (a.state === 'taken') return { tone: 'bad', text: 'Already taken' };
  if (a.state === 'invalid') return { tone: 'bad', text: '3–32 chars, start with a letter, letters/numbers/underscore.' };
  return undefined;
}

function Field({ label, error, hint, children }: {
  label: string; error?: string | null; hint?: Hint; children: React.ReactNode;
}) {
  const tone = error ? 'bad' : hint?.tone;
  const color = tone === 'ok' ? 'var(--tg-success)' : tone === 'bad' ? 'var(--tg-danger)' : 'var(--tg-text-dim)';
  return (
    <div className="stack" style={{ gap: 6 }}>
      <label className="label">{label}</label>
      {children}
      {(error || hint) && (
        <span style={{ fontSize: 11, color, fontFamily: 'IBM Plex Mono, monospace' }}>
          {error || hint?.text}
        </span>
      )}
    </div>
  );
}
