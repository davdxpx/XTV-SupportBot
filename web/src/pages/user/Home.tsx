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
  const { data: tickets } = useQuery({
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
      <section className="stack" style={{ gap: 4 }}>
        <h2 style={{ margin: 0 }}>Hey {me?.first_name ?? 'there'} 👋</h2>
        {me?.brand_tagline && <p className="muted" style={{ margin: 0 }}>{me.brand_tagline}</p>}
      </section>

      <section className="stats-grid">
        <Stat label="Open" value={open} />
        <Stat label="Waiting for you" value={waiting} highlight={waiting > 0} />
        <Stat label="Closed this month" value={closedThisMonth} />
      </section>

      <section className="stack" style={{ gap: 10 }}>
        <Link to="/new" className="btn btn-primary" style={{ textAlign: 'center' }}>
          📮 Open a new ticket
        </Link>
        <SecondaryLink
          to="/tickets"
          icon="🗂"
          label="My tickets"
          badge={waiting > 0 ? `${waiting} new` : undefined}
        />
        <SecondaryLink to="/settings" icon="⚙️" label="Settings" />
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
  icon,
  label,
  badge,
}: {
  to: string;
  icon: string;
  label: string;
  badge?: string;
}) {
  return (
    <Link to={to} className="ticket-item row" style={{ padding: '14px 16px' }}>
      <span style={{ fontSize: 18 }}>{icon}</span>
      <span style={{ flex: 1 }}>{label}</span>
      {badge && <span className="pill pill-warn">{badge}</span>}
    </Link>
  );
}
