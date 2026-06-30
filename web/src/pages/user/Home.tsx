import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api, getMe } from '@/lib/api';

interface MyTicketsResponse {
  items: Array<{
    id: string;
    status: string;
    last_admin_msg_at: string | null;
    last_user_msg_at: string | null;
    closed_at: string | null;
  }>;
  count: number;
}

export function UserHome() {
  const { data: me } = useQuery({ queryKey: ['me'], queryFn: getMe });
  const { data: tickets, isLoading: ticketsLoading } = useQuery({
    queryKey: ['my-tickets-home'],
    queryFn: () => api<MyTicketsResponse>('/api/v1/me/tickets?limit=100'),
  });

  const open = tickets?.items.filter((t) => t.status === 'open').length ?? 0;
  const waiting =
    tickets?.items.filter((t) => t.status === 'open' && t.last_admin_msg_at !== null).length ?? 0;
  const closedThisMonth = (() => {
    if (!tickets) return 0;
    const now = new Date();
    return tickets.items.filter((t) => {
      if (t.status !== 'closed' || !t.closed_at) return false;
      const c = new Date(t.closed_at);
      return c.getFullYear() === now.getFullYear() && c.getMonth() === now.getMonth();
    }).length;
  })();

  return (
    <div className="stack-lg stack">
      <section style={{ display: 'flex', flexDirection: 'column', gap: 4, marginBottom: 24 }}>
        <h2 style={{ margin: 0, fontSize: 24, fontWeight: 600, letterSpacing: '-0.02em' }}>
          Hello, {me?.first_name ?? 'there'}.
        </h2>
        <p style={{ margin: 0, color: 'var(--tg-text-dim)', fontSize: 15 }}>
          {me?.brand_tagline ?? "How can we help you today?"}
        </p>
      </section>

      <section style={{ marginBottom: 24 }}>
        <Link to="/new" className="btn btn-primary" style={{ width: '100%', padding: '16px', fontSize: 16 }}>
          Start a new request
        </Link>
      </section>

      <section className="stats-grid" style={{ marginBottom: 24 }}>
        {ticketsLoading ? (
          <>
            <div className="skeleton skeleton-block" />
            <div className="skeleton skeleton-block" />
            <div className="skeleton skeleton-block" />
          </>
        ) : (
          <>
            <Stat label="ACTIVE" value={open} />
            <Stat label="ACTION REQUIRED" value={waiting} highlight={waiting > 0} />
            <Stat label="RESOLVED" value={closedThisMonth} />
          </>
        )}
      </section>

      <section style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <SecondaryLink
          to="/tickets"
          label="View my tickets"
          badge={waiting > 0 ? `${waiting} ACTION REQUIRED` : undefined}
        />
        <SecondaryLink to="/settings" label="Configure preferences" />
      </section>
    </div>
  );
}

function Stat({
  label,
  value,
  highlight = false,
}: {
  label: string;
  value: number;
  highlight?: boolean;
}) {
  return (
    <div className={`stat${highlight ? ' stat-highlight' : ''}`}>
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}

function SecondaryLink({
  to,
  label,
  badge,
}: {
  to: string;
  label: string;
  badge?: string;
}) {
  return (
    <Link to={to} className="ticket-item" style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
      <span style={{ flex: 1, fontWeight: 500 }}>{label}</span>
      {badge && <span className="chip chip-active">{badge}</span>}
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square">
        <polyline points="9 18 15 12 9 6"></polyline>
      </svg>
    </Link>
  );
}
