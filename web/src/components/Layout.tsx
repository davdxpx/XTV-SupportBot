import { Link, Outlet, useNavigate } from 'react-router-dom';
import { clearApiKey } from '@/lib/api';

export function Layout() {
  const navigate = useNavigate();
  const logout = () => {
    clearApiKey();
    navigate('/login');
  };

  return (
    <div style={{ fontFamily: 'system-ui, sans-serif' }}>
      <header
        style={{
          display: 'flex',
          alignItems: 'center',
          padding: '12px 24px',
          borderBottom: '1px solid #e5e7eb',
          gap: 24,
        }}
      >
        <strong>XTV-SupportBot</strong>
        <nav style={{ display: 'flex', gap: 16 }}>
          <Link to="/">Dashboard</Link>
          <Link to="/tickets">Tickets</Link>
        </nav>
        <div style={{ marginLeft: 'auto' }}>
          <button onClick={logout}>Logout</button>
        </div>
      </header>
      <main style={{ padding: 24 }}>
        <Outlet />
      </main>
    </div>
  );
}
