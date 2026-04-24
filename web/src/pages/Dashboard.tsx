import { useQuery } from '@tanstack/react-query';
import { analyticsSummary } from '@/lib/api';

export function Dashboard() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['analytics-summary', 7],
    queryFn: () => analyticsSummary(7),
  });

  if (isLoading) return <p>Loading analytics…</p>;
  if (error) return <p style={{ color: 'crimson' }}>Failed to load analytics.</p>;
  if (!data) return null;

  return (
    <div>
      <h2>Last {data.days} days</h2>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: 16,
        }}
      >
        <StatCard label="Tickets" value={data.tickets.toString()} />
        <StatCard label="SLA breached" value={data.sla_breached.toString()} />
        <StatCard label="SLA total" value={data.sla_total.toString()} />
        <StatCard
          label="Compliance"
          value={`${Math.round(data.sla_compliance_ratio * 100)}%`}
        />
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div
      style={{
        padding: 16,
        border: '1px solid #e5e7eb',
        borderRadius: 8,
      }}
    >
      <div style={{ color: '#666', fontSize: 12 }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 600, marginTop: 4 }}>{value}</div>
    </div>
  );
}
