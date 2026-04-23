import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { setApiKey } from '@/lib/api';

export function Login() {
  const [value, setValue] = useState('');
  const navigate = useNavigate();

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!value.trim()) return;
    setApiKey(value.trim());
    navigate('/');
  };

  return (
    <div
      style={{
        maxWidth: 420,
        margin: '10vh auto',
        fontFamily: 'system-ui, sans-serif',
      }}
    >
      <h1>XTV-SupportBot</h1>
      <p>Paste your API key to continue.</p>
      <form onSubmit={onSubmit}>
        <input
          type="password"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="xtv_…"
          style={{ width: '100%', padding: 8, fontSize: 16 }}
          autoFocus
        />
        <button
          type="submit"
          disabled={!value.trim()}
          style={{ marginTop: 12, padding: '8px 16px' }}
        >
          Sign in
        </button>
      </form>
      <p style={{ marginTop: 16, color: '#666', fontSize: 13 }}>
        Generate a key in the bot with <code>/apikey create admin:full</code>.
      </p>
    </div>
  );
}
