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
    <div className="stack stack-lg">
      <div className="heading-row">
        <h1 className="heading">Overview</h1>
      </div>

      <section
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: 14,
        }}
      >
        <StatCard label="Open tickets" value={String(open)} />
        <StatCard
          label="Unassigned"
          value={String(unassigned)}
          highlight={unassigned > 0}
        />
        {analytics.data && (
          <>
            <StatCard label="7-day tickets" value={String(analytics.data.tickets)} />
            <StatCard
              label="SLA compliance"
              value={`${Math.round(analytics.data.sla_compliance_ratio * 100)}%`}
              highlight={analytics.data.sla_compliance_ratio < 0.9}
            />
          </>
        )}
      </section>

      <section className="row" style={{ flexWrap: 'wrap' }}>
        <Link to="/admin/inbox" className="btn btn-ghost">Open inbox →</Link>
        <Link to="/admin/projects" className="btn btn-ghost">Manage projects →</Link>
        <Link to="/admin/rules" className="btn btn-ghost">Automation rules →</Link>
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
    <div className={`card${highlight ? ' stat-highlight' : ''}`}>
      <div className="muted" style={{ fontSize: 12 }}>{label}</div>
      <div style={{ fontSize: 30, fontWeight: 700, marginTop: 4 }}>{value}</div>
    </div>
  );
}
