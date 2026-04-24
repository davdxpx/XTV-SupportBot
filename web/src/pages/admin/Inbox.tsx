import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { listTickets, type Ticket } from '@/lib/api';

type View = 'open' | 'unassigned' | 'closed' | 'all';

const VIEWS: Array<{ key: View; label: string }> = [
  { key: 'open', label: 'Open' },
  { key: 'unassigned', label: 'Unassigned' },
  { key: 'closed', label: 'Closed' },
  { key: 'all', label: 'All' },
];

export function Inbox() {
  const [view, setView] = useState<View>('open');
  const params = new URLSearchParams({ limit: '100' });
  if (view === 'open' || view === 'closed') params.set('status', view);
  const { data, isLoading } = useQuery({
    queryKey: ['admin-tickets', view],
    queryFn: () => listTickets(params),
  });

  const items: Ticket[] =
    view === 'unassigned'
      ? (data?.items ?? []).filter((t) => t.status === 'open' && !t.assignee_id)
      : (data?.items ?? []);

  return (
    <div className="stack stack-lg">
      <div className="heading-row">
        <h1 className="heading">Inbox</h1>
      </div>
      <div className="chips">
        {VIEWS.map((v) => (
          <button
            key={v.key}
            type="button"
            onClick={() => setView(v.key)}
            className={`chip${v.key === view ? ' chip-active' : ''}`}
          >
            {v.label}
          </button>
        ))}
      </div>

      {isLoading && <p className="muted">Loading…</p>}
      {!isLoading && items.length === 0 && (
        <p className="muted">No tickets in this view.</p>
      )}

      {items.length > 0 && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Status</th>
              <th>Priority</th>
              <th>User</th>
              <th>Tags</th>
              <th>Created</th>
              <th>Assignee</th>
            </tr>
          </thead>
          <tbody>
            {items.map((t) => (
              <tr key={t._id}>
                <td>
                  <Link to={`/admin/tickets/${t._id}`}>{t.status}</Link>
                </td>
                <td>{t.priority ?? '—'}</td>
                <td>{t.user_id}</td>
                <td>
                  {(t.tags ?? []).map((tag) => (
                    <span key={tag} className="pill pill-muted" style={{ marginRight: 4 }}>
                      #{tag}
                    </span>
                  ))}
                </td>
                <td>{t.created_at ? new Date(t.created_at).toLocaleString() : '—'}</td>
                <td>{t.assignee_id ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
