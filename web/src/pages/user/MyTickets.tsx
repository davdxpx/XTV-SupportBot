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
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <h2 style={{ margin: 0 }}>🗂 My tickets</h2>

      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        {FILTERS.map((f) => {
          const active = f.key === filter;
          return (
            <button
              key={f.key}
              type="button"
              onClick={() => setFilter(f.key)}
              style={{
                padding: '6px 12px',
                borderRadius: 999,
                border: active ? '1px solid #2563eb' : '1px solid #e5e7eb',
                background: active ? '#2563eb' : 'transparent',
                color: active ? '#ffffff' : 'inherit',
                cursor: 'pointer',
                fontSize: 13,
              }}
            >
              {f.label}
            </button>
          );
        })}
      </div>

      {isLoading && <p>Loading…</p>}

      {data && data.items.length === 0 && (
        <div style={{ opacity: 0.7, padding: 24, textAlign: 'center' }}>
          No tickets in this view.
          <br />
          <Link to="/new" style={{ color: '#2563eb' }}>
            Open a new one →
          </Link>
        </div>
      )}

      <ul
        style={{
          listStyle: 'none',
          padding: 0,
          margin: 0,
          display: 'flex',
          flexDirection: 'column',
          gap: 8,
        }}
      >
        {data?.items.map((t) => (
          <li key={t.id}>
            <Link
              to={`/tickets/${t.id}`}
              style={{
                display: 'block',
                padding: '12px 14px',
                border: '1px solid #e5e7eb',
                borderRadius: 10,
                textDecoration: 'none',
                color: 'inherit',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  gap: 8,
                  alignItems: 'center',
                  fontSize: 12,
                  opacity: 0.7,
                }}
              >
                <StatusBadge status={t.status} />
                {t.priority && <span>· {t.priority}</span>}
                {t.updated_at && (
                  <span style={{ marginLeft: 'auto' }}>
                    {new Date(t.updated_at).toLocaleDateString()}
                  </span>
                )}
              </div>
              <div style={{ marginTop: 4, fontSize: 14 }}>
                {t.subject || '(no message preview)'}
              </div>
              {t.tags && t.tags.length > 0 && (
                <div
                  style={{
                    marginTop: 6,
                    display: 'flex',
                    gap: 4,
                    flexWrap: 'wrap',
                  }}
                >
                  {t.tags.map((tag) => (
                    <span
                      key={tag}
                      style={{
                        fontSize: 11,
                        padding: '2px 6px',
                        borderRadius: 6,
                        background: '#f3f4f6',
                      }}
                    >
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
  const colors: Record<string, { bg: string; fg: string }> = {
    open: { bg: '#dcfce7', fg: '#166534' },
    closed: { bg: '#f3f4f6', fg: '#374151' },
  };
  const c = colors[status] ?? { bg: '#fef3c7', fg: '#92400e' };
  return (
    <span
      style={{
        background: c.bg,
        color: c.fg,
        padding: '2px 8px',
        borderRadius: 999,
        fontSize: 11,
        fontWeight: 600,
      }}
    >
      {status}
    </span>
  );
}
