import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

interface Rule {
  id: string;
  name: string;
  enabled: boolean;
  trigger: string;
  conditions: Array<{ field: string; op: string; value: unknown }>;
  actions: Array<{ name: string; params?: Record<string, unknown> }>;
}

interface RulesResponse {
  items: Rule[];
  count: number;
}

export function Rules() {
  const { data, isLoading } = useQuery({
    queryKey: ['admin-rules'],
    queryFn: () => api<RulesResponse>('/api/v1/rules'),
  });

  return (
    <div className="stack stack-lg">
      <div className="heading-row">
        <h1 className="heading">Automation rules</h1>
      </div>
      <p className="muted" style={{ fontSize: 13 }}>
        Read-only view. Use <code>/admin → Rules</code> in the bot to create, edit,
        or toggle rules — the full builder GUI lands in a later phase.
      </p>

      {isLoading && <p className="muted">Loading…</p>}
      {data && data.items.length === 0 && (
        <p className="muted">No rules configured yet.</p>
      )}

      <ul className="ticket-list">
        {data?.items.map((r) => (
          <li key={r.id} className="card stack" style={{ gap: 8 }}>
            <div className="row">
              <strong>{r.name}</strong>
              <span className={`pill ${r.enabled ? 'pill-success' : 'pill-muted'}`}>
                {r.enabled ? 'enabled' : 'disabled'}
              </span>
              <span className="muted" style={{ marginLeft: 'auto', fontSize: 12 }}>
                on {r.trigger}
              </span>
            </div>

            {r.conditions.length > 0 && (
              <div style={{ fontSize: 13 }}>
                <strong>WHEN</strong>{' '}
                {r.conditions.map((c, i) => (
                  <span key={i}>
                    {i > 0 && ' AND '}
                    <code>
                      {c.field} {c.op} {JSON.stringify(c.value)}
                    </code>
                  </span>
                ))}
              </div>
            )}
            <div style={{ fontSize: 13 }}>
              <strong>THEN</strong>{' '}
              {r.actions.map((a, i) => (
                <span key={i}>
                  {i > 0 && ', '}
                  <code>{a.name}</code>
                  {a.params && Object.keys(a.params).length > 0 && (
                    <span className="muted">({JSON.stringify(a.params)})</span>
                  )}
                </span>
              ))}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
