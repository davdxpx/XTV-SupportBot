import { useQuery } from '@tanstack/react-query';
import { listTickets } from '@/lib/api';

export function Tickets() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['tickets'],
    queryFn: () => listTickets(new URLSearchParams({ limit: '50' })),
  });

  if (isLoading) return <p>Loading tickets…</p>;
  if (error) return <p style={{ color: 'crimson' }}>Failed to load tickets.</p>;
  if (!data) return null;

  return (
    <div>
      <h2>Tickets ({data.count})</h2>
      <table
        style={{
          width: '100%',
          borderCollapse: 'collapse',
          fontSize: 14,
        }}
      >
        <thead>
          <tr style={{ borderBottom: '1px solid #e5e7eb', textAlign: 'left' }}>
            <th style={{ padding: 8 }}>ID</th>
            <th style={{ padding: 8 }}>Status</th>
            <th style={{ padding: 8 }}>Priority</th>
            <th style={{ padding: 8 }}>User</th>
            <th style={{ padding: 8 }}>Project</th>
            <th style={{ padding: 8 }}>Team</th>
            <th style={{ padding: 8 }}>Tags</th>
            <th style={{ padding: 8 }}>Created</th>
          </tr>
        </thead>
        <tbody>
          {data.items.map((t) => (
            <tr
              key={t._id}
              style={{ borderBottom: '1px solid #f3f4f6' }}
            >
              <td style={{ padding: 8, fontFamily: 'monospace' }}>
                {t._id.slice(-8)}
              </td>
              <td style={{ padding: 8 }}>{t.status}</td>
              <td style={{ padding: 8 }}>{t.priority ?? '—'}</td>
              <td style={{ padding: 8 }}>{t.user_id}</td>
              <td style={{ padding: 8 }}>{t.project_id ?? '—'}</td>
              <td style={{ padding: 8 }}>{t.team_id ?? '—'}</td>
              <td style={{ padding: 8 }}>
                {(t.tags ?? []).join(', ') || '—'}
              </td>
              <td style={{ padding: 8 }}>
                {t.created_at ? new Date(t.created_at).toLocaleString() : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
