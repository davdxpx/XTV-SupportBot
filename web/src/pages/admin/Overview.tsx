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
    <div style={{ display: 'flex', flexDirection: 'column', gap: 32 }}>
      <div className="heading-row" style={{ marginBottom: 0 }}>
        <div>
          <h1 className="heading">SYSTEM OVERVIEW</h1>
          <div className="heading-mono" style={{ marginTop: 4 }}>Status & Metrics</div>
        </div>
      </div>

      <section
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: 16,
        }}
      >
        <StatCard label="ACTIVE REQUESTS" value={String(open)} />
        <StatCard
          label="UNASSIGNED"
          value={String(unassigned)}
          highlight={unassigned > 0}
        />
        {analytics.data ? (
          <>
            <StatCard label="VOL (7D)" value={String(analytics.data.tickets)} />
            <StatCard
              label="SLA COMPLIANCE"
              value={`${Math.round(analytics.data.sla_compliance_ratio * 100)}%`}
              highlight={analytics.data.sla_compliance_ratio < 0.9}
            />
          </>
        ) : (
          <>
            <div className="skeleton skeleton-block" style={{ height: 100 }} />
            <div className="skeleton skeleton-block" style={{ height: 100 }} />
          </>
        )}
      </section>

      <section style={{ display: 'flex', gap: 16, borderTop: '1px solid var(--tg-border)', paddingTop: 24 }}>
        <Link to="/admin/inbox" className="btn btn-primary">OPEN TRIAGE QUEUE</Link>
        <Link to="/admin/projects" className="btn btn-ghost">SYSTEM CONFIGURATION</Link>
      </section>
    </div>
  );
}

function StatCard({
  label,
  value,
  highlight = false,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div style={{
      padding: 16,
      border: '1px solid var(--tg-border)',
      background: highlight ? 'var(--tg-accent-soft)' : 'var(--tg-surface)',
      borderLeftWidth: 4,
      borderLeftColor: highlight ? 'var(--tg-accent)' : 'var(--tg-border)',
      display: 'flex',
      flexDirection: 'column',
      gap: 12
    }}>
      <div style={{
        fontSize: 11, fontFamily: 'IBM Plex Mono, monospace',
        color: highlight ? 'var(--tg-accent)' : 'var(--tg-text-dim)',
        textTransform: 'uppercase'
      }}>
        {label}
      </div>
      <div style={{
        fontSize: 32, fontFamily: 'IBM Plex Mono, monospace',
        fontWeight: 400, color: 'var(--tg-text)', lineHeight: 1
      }}>
        {value}
      </div>
    </div>
  );
}
