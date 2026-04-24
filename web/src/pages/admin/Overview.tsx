import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { analyticsSummary, listTickets } from '@/lib/api';

export function Overview() {
  const analytics = useQuery({
    queryKey: ['analytics-summary', 7],
    queryFn: () => analyticsSummary(7),
  });
  const tickets = useQuery({
    queryKey: ['tickets-overview'],
    queryFn: () => listTickets(new URLSearchParams({ limit: '200' })),
  });

  const open = tickets.data?.items.filter((t) => t.status === 'open').length ?? 0;
  const unassigned =
    tickets.data?.items.filter((t) => t.status === 'open' && !t.assignee_id).length ?? 0;

  return (
    <div>
      <h1 style={{ marginTop: 0 }}>Overview</h1>

      <section
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: 12,
        }}
      >
        <StatCard label="Open tickets" value={String(open)} accent="#2563eb" />
        <StatCard
          label="Unassigned"
          value={String(unassigned)}
          accent={unassigned > 0 ? '#d97706' : '#2563eb'}
        />
        {analytics.data && (
          <>
            <StatCard label="Last 7 days · tickets" value={String(analytics.data.tickets)} />
            <StatCard
              label="SLA compliance"
              value={`${Math.round(analytics.data.sla_compliance_ratio * 100)}%`}
              accent={
                analytics.data.sla_compliance_ratio >= 0.9 ? '#059669' : '#d97706'
              }
            />
          </>
        )}
      </section>

      <section style={{ marginTop: 24, display: 'flex', gap: 12, flexWrap: 'wrap' }}>
        <QuickLink to="/admin/inbox" label="Open inbox" />
        <QuickLink to="/admin/projects" label="Manage projects" />
        <QuickLink to="/admin/rules" label="Automation rules" />
      </section>
    </div>
  );
}

function StatCard({
  label,
  value,
  accent = '#2563eb',
}: {
  label: string;
  value: string;
  accent?: string;
}) {
  return (
    <div
      style={{
        padding: 16,
        border: '1px solid #e5e7eb',
        borderRadius: 10,
        borderTop: `3px solid ${accent}`,
      }}
    >
      <div style={{ color: '#6b7280', fontSize: 12 }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 700, marginTop: 4 }}>{value}</div>
    </div>
  );
}

function QuickLink({ to, label }: { to: string; label: string }) {
  return (
    <Link
      to={to}
      style={{
        padding: '10px 16px',
        border: '1px solid #e5e7eb',
        borderRadius: 10,
        textDecoration: 'none',
        color: '#111827',
      }}
    >
      {label} →
    </Link>
  );
}
