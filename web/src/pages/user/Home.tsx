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
    queryKey: ['my-tickets'],
    queryFn: () => api<MyTicketsResponse>('/api/v1/me/tickets?limit=100'),
  });

  const open =
    tickets?.items.filter((t) => t.status === 'open').length ?? 0;
  const waiting =
    tickets?.items.filter(
      (t) => t.status === 'open' && t.last_admin_msg_at !== null,
    ).length ?? 0;
  const closedThisMonth = (() => {
    if (!tickets) return 0;
    const now = new Date();
    return tickets.items.filter((t) => {
      if (t.status !== 'closed' || !t.closed_at) return false;
      const c = new Date(t.closed_at);
      return (
        c.getFullYear() === now.getFullYear() &&
        c.getMonth() === now.getMonth()
      );
    }).length;
  })();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <section>
        <h2 style={{ margin: '4px 0' }}>
          Hey {me?.first_name ?? 'there'} 👋
        </h2>
        {me?.brand_tagline && (
          <p style={{ margin: 0, opacity: 0.7 }}>{me.brand_tagline}</p>
        )}
      </section>

      <section
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 8,
        }}
      >
        <Stat label="Open" value={open} />
        <Stat label="Waiting for you" value={waiting} highlight={waiting > 0} />
        <Stat label="Closed this month" value={closedThisMonth} />
      </section>

      <section style={{ display: 'grid', gap: 10 }}>
        <PrimaryLink to="/new" icon="📮" label="Open a new ticket" />
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
    <div
      style={{
        padding: '12px 10px',
        border: `1px solid ${highlight ? '#f59e0b' : '#e5e7eb'}`,
        background: highlight ? '#fef3c7' : 'transparent',
        borderRadius: 10,
        textAlign: 'center',
      }}
    >
      <div style={{ fontSize: 22, fontWeight: 700 }}>{value}</div>
      <div style={{ fontSize: 11, opacity: 0.75 }}>{label}</div>
    </div>
  );
}

function PrimaryLink({
  to,
  icon,
  label,
}: {
  to: string;
  icon: string;
  label: string;
}) {
  return (
    <Link
      to={to}
      style={{
        padding: '14px 18px',
        background: '#2563eb',
        color: '#ffffff',
        textDecoration: 'none',
        borderRadius: 12,
        fontWeight: 600,
        display: 'flex',
        alignItems: 'center',
        gap: 10,
      }}
    >
      <span>{icon}</span>
      <span>{label}</span>
    </Link>
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
    <Link
      to={to}
      style={{
        padding: '12px 18px',
        border: '1px solid #e5e7eb',
        color: 'inherit',
        textDecoration: 'none',
        borderRadius: 12,
        display: 'flex',
        alignItems: 'center',
        gap: 10,
      }}
    >
      <span>{icon}</span>
      <span style={{ flex: 1 }}>{label}</span>
      {badge && (
        <span
          style={{
            background: '#fef3c7',
            color: '#92400e',
            padding: '2px 8px',
            borderRadius: 999,
            fontSize: 12,
            fontWeight: 600,
          }}
        >
          {badge}
        </span>
      )}
    </Link>
  );
}
