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
    <div>
      <h1 style={{ marginTop: 0 }}>Inbox</h1>
      <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
        {VIEWS.map((v) => {
          const active = v.key === view;
          return (
            <button
              key={v.key}
              type="button"
              onClick={() => setView(v.key)}
              style={{
                padding: '6px 14px',
                borderRadius: 999,
                border: active ? '1px solid #2563eb' : '1px solid #e5e7eb',
                background: active ? '#2563eb' : 'transparent',
                color: active ? '#ffffff' : 'inherit',
                cursor: 'pointer',
              }}
            >
              {v.label}
            </button>
          );
        })}
      </div>

      {isLoading && <p>Loading…</p>}
      {!isLoading && items.length === 0 && (
        <p style={{ opacity: 0.7 }}>No tickets in this view.</p>
      )}

      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: '1px solid #e5e7eb', textAlign: 'left' }}>
            <Th>Status</Th>
            <Th>Priority</Th>
            <Th>User</Th>
            <Th>Tags</Th>
            <Th>Created</Th>
            <Th>Assignee</Th>
          </tr>
        </thead>
        <tbody>
          {items.map((t) => (
            <tr
              key={t._id}
              style={{ borderBottom: '1px solid #f3f4f6', cursor: 'pointer' }}
            >
              <Td>
                <Link
                  to={`/admin/tickets/${t._id}`}
                  style={{ color: '#2563eb', textDecoration: 'none' }}
                >
                  {t.status}
                </Link>
              </Td>
              <Td>{t.priority ?? '—'}</Td>
              <Td>{t.user_id}</Td>
              <Td>
                {(t.tags ?? []).map((tag) => (
                  <span
                    key={tag}
                    style={{
                      background: '#f3f4f6',
                      padding: '2px 6px',
                      borderRadius: 6,
                      marginRight: 4,
                      fontSize: 11,
                    }}
                  >
                    #{tag}
                  </span>
                ))}
              </Td>
              <Td>
                {t.created_at
                  ? new Date(t.created_at).toLocaleString()
                  : '—'}
              </Td>
              <Td>{t.assignee_id ?? '—'}</Td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th style={{ padding: '8px 10px', fontSize: 12, color: '#6b7280', fontWeight: 500 }}>
      {children}
    </th>
  );
}

function Td({ children }: { children: React.ReactNode }) {
  return <td style={{ padding: '10px', fontSize: 14 }}>{children}</td>;
}
