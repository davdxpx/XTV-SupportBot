import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { analyticsSummary, ticketStats } from '@/lib/api';

export function Overview() {
  const analytics = useQuery({
    queryKey: ['analytics-summary', 7],
    queryFn: () => analyticsSummary(7),
  });
  // Live counts from the tickets collection — independent of the nightly
  // analytics rollup, so the console reflects reality immediately.
  const stats = useQuery({
    queryKey: ['ticket-stats'],
    queryFn: ticketStats,
  });

  const open = stats.data?.open ?? 0;
  const unassigned = stats.data?.unassigned ?? 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 32 }}>
      <div className="heading-row" style={{ marginBottom: 0 }}>
        <div>
          <h1 className="heading">SYSTEM OVERVIEW</h1>
          <div className="heading-mono" style={{ marginTop: 4 }}>Status & Metrics</div>
        </div>
      </div>

      <section className="admin-stats">
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
