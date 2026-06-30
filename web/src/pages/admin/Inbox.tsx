import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { listTickets, type Ticket } from '@/lib/api';

type View = 'open' | 'unassigned' | 'closed' | 'all';

const VIEWS: Array<{ key: View; label: string }> = [
  { key: 'open', label: 'ACTIVE' },
  { key: 'unassigned', label: 'UNASSIGNED' },
  { key: 'closed', label: 'RESOLVED' },
  { key: 'all', label: 'ALL RECORDS' },
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
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div className="heading-row" style={{ marginBottom: 0, paddingBottom: 0, borderBottom: 'none' }}>
        <div>
          <h1 className="heading">TRIAGE QUEUE</h1>
        </div>
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

      {isLoading && (
        <div style={{ padding: 32, textAlign: 'center', fontFamily: 'IBM Plex Mono, monospace', color: 'var(--tg-text-dim)' }}>
          RETRIEVING RECORDS...
        </div>
      )}
      {!isLoading && items.length === 0 && (
        <div style={{ padding: 32, textAlign: 'center', border: '1px dashed var(--tg-border)', fontFamily: 'IBM Plex Mono, monospace', color: 'var(--tg-text-dim)' }}>
          NO RECORDS MATCH QUERY
        </div>
      )}

      {items.length > 0 && (
        <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th style={{ width: 120 }}>ID</th>
              <th style={{ width: 100 }}>STATUS</th>
              <th>SUBJECT / USER</th>
              <th>TAGS</th>
              <th style={{ width: 160 }}>ASSIGNEE</th>
              <th style={{ width: 140, textAlign: 'right' }}>SLA / CREATED</th>
            </tr>
          </thead>
          <tbody>
            {items.map((t) => (
              <tr key={t._id}>
                <td className="mono">
                  <Link to={`/admin/tickets/${t._id}`} style={{ color: 'var(--tg-text)', textDecoration: 'none' }}>
                    {t._id.slice(-6).toUpperCase()}
                  </Link>
                </td>
                <td className="mono" style={{ color: t.status === 'open' ? 'var(--tg-success)' : 'var(--tg-text-dim)' }}>
                  {t.status.toUpperCase()}
                </td>
                <td>
                  <Link to={`/admin/tickets/${t._id}`} style={{ display: 'flex', flexDirection: 'column', color: 'var(--tg-text)', textDecoration: 'none' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 14, color: 'var(--tg-text)', marginTop: 2 }}>
                      <span className="mono">{t.user_id}</span>
                      {(t.is_vip || t.display_badge) && (
                        <span style={{
                          fontSize: 10, fontFamily: 'IBM Plex Mono, monospace',
                          padding: '0 4px', background: 'var(--tg-accent-soft)', color: 'var(--tg-accent)', border: '1px solid var(--tg-accent)'
                        }}>
                          {t.display_badge || t.tier_label || 'VIP'}
                        </span>
                      )}
                    </div>
                  </Link>
                </td>
                <td>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {(t.tags ?? []).map((tag) => (
                      <span key={tag} style={{
                        fontSize: 10, fontFamily: 'IBM Plex Mono, monospace',
                        padding: '2px 6px', background: 'var(--tg-surface-hi)', color: 'var(--tg-text-dim)', border: '1px solid var(--tg-border)'
                      }}>
                        {tag}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="mono">{t.assignee_id ?? '--'}</td>
                <td className="mono right" style={{ color: 'var(--tg-text-dim)' }}>
                  {t.created_at ? new Date(t.created_at).toISOString().replace('T', ' ').slice(0, 16) : '--'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      )}
    </div>
  );
}
