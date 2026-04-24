import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

type Filter = 'all' | 'open' | 'waiting' | 'closed';

interface TicketSummary {
  id: string;
  status: string;
  subject: string;
  priority?: string | null;
  tags?: string[];
  updated_at: string | null;
  last_admin_msg_at: string | null;
}

interface TicketsResponse {
  items: TicketSummary[];
  count: number;
}

const FILTERS: { key: Filter; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'open', label: 'Open' },
  { key: 'waiting', label: 'Waiting' },
  { key: 'closed', label: 'Closed' },
];

export function MyTickets() {
  const [filter, setFilter] = useState<Filter>('all');
  const { data, isLoading } = useQuery({
    queryKey: ['my-tickets', filter],
    queryFn: () =>
      api<TicketsResponse>(
        filter === 'all'
          ? '/api/v1/me/tickets?limit=50'
          : `/api/v1/me/tickets?status=${filter}&limit=50`,
      ),
  });

  return (
    <div className="stack stack-lg">
      <h2 className="heading">🗂 My tickets</h2>

      <div className="chips">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            type="button"
            onClick={() => setFilter(f.key)}
            className={`chip${f.key === filter ? ' chip-active' : ''}`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {isLoading && <p className="muted">Loading…</p>}

      {data && data.items.length === 0 && (
        <div className="muted" style={{ padding: 24, textAlign: 'center' }}>
          No tickets in this view.
          <br />
          <Link to="/new">Open a new one →</Link>
        </div>
      )}

      <ul className="ticket-list">
        {data?.items.map((t) => (
          <li key={t.id}>
            <Link to={`/tickets/${t.id}`} className="ticket-item">
              <div className="ticket-meta">
                <StatusBadge status={t.status} />
                {t.priority && <span>· {t.priority}</span>}
                {t.updated_at && (
                  <span className="ticket-date">
                    {new Date(t.updated_at).toLocaleDateString()}
                  </span>
                )}
              </div>
              <div className="ticket-subject">{t.subject || '(no preview)'}</div>
              {t.tags && t.tags.length > 0 && (
                <div className="ticket-tags">
                  {t.tags.map((tag) => (
                    <span key={tag} className="pill pill-muted">
                      #{tag}
                    </span>
                  ))}
                </div>
              )}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    open: 'pill pill-success',
    closed: 'pill pill-muted',
  };
  return <span className={map[status] ?? 'pill pill-warn'}>{status}</span>;
}
