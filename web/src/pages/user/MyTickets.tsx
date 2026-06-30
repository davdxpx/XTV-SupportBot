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
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['my-tickets', filter],
    queryFn: () =>
      api<TicketsResponse>(
        filter === 'all'
          ? '/api/v1/me/tickets?limit=50'
          : `/api/v1/me/tickets?status=${filter}&limit=50`,
      ),
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <header>
        <h2 style={{ margin: 0, fontSize: 24, fontWeight: 600, letterSpacing: '-0.02em' }}>TICKETS</h2>
      </header>

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

      {isError && (
        <div style={{ padding: 12, border: '1px solid var(--tg-danger)', background: 'var(--tg-danger-soft)', color: 'var(--tg-text)', fontSize: 13, fontFamily: 'IBM Plex Mono, monospace' }}>
          ERROR: {String(error)}
        </div>
      )}

      {isLoading && (
        <ul className="ticket-list">
          {[0, 1, 2, 3].map((i) => (
            <li key={i}>
              <div className="ticket-item">
                <span className="skeleton skeleton-line" style={{ width: '40%' }} />
                <span className="skeleton skeleton-line" style={{ width: '70%' }} />
              </div>
            </li>
          ))}
        </ul>
      )}

      {data && data.items.length === 0 && (
        <div style={{ padding: 32, textAlign: 'center', border: '1px dashed var(--tg-border)' }}>
          <div style={{ color: 'var(--tg-text-dim)', marginBottom: 12, fontFamily: 'IBM Plex Mono, monospace', textTransform: 'uppercase' }}>
            No records found
          </div>
          <Link to="/new" className="btn btn-primary btn-sm">
            Start a new request
          </Link>
        </div>
      )}

      <ul className="ticket-list">
        {data?.items.map((t) => {
          const isOpen = t.status === 'open';
          const isWaiting = isOpen && t.last_admin_msg_at !== null;
          return (
            <li key={t.id}>
              <Link
                to={`/tickets/${t.id}`}
                className="ticket-item"
                style={{
                  borderLeftColor: isWaiting ? 'var(--tg-accent)' : (isOpen ? 'var(--tg-success)' : 'var(--tg-border)')
                }}
              >
                <div className="ticket-meta">
                  <span style={{
                    color: isOpen ? (isWaiting ? 'var(--tg-accent)' : 'var(--tg-success)') : 'var(--tg-text-dim)',
                    fontWeight: 600
                  }}>
                    {isWaiting ? 'ACTION REQUIRED' : t.status.toUpperCase()}
                  </span>
                  {t.priority && <span>/ {t.priority}</span>}
                  <span className="ticket-date">
                    {t.updated_at ? new Date(t.updated_at).toISOString().split('T')[0] : ''}
                  </span>
                </div>
                <div className="ticket-subject">{t.subject || '(untitled)'}</div>
                {t.tags && t.tags.length > 0 && (
                  <div className="ticket-tags">
                    {t.tags.map((tag) => (
                      <span key={tag} style={{
                        fontSize: 10, fontFamily: 'IBM Plex Mono, monospace',
                        padding: '2px 6px', background: 'var(--tg-surface-hi)', color: 'var(--tg-text-dim)'
                      }}>
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
              </Link>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
