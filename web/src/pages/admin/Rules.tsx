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
    <div>
      <h1 style={{ marginTop: 0 }}>Automation rules</h1>
      <p style={{ opacity: 0.7, fontSize: 13 }}>
        Read-only view. Use <code>/admin → Rules</code> in the bot to create,
        edit, or toggle rules — the full builder GUI lands in a later phase.
      </p>

      {isLoading && <p>Loading…</p>}
      {data && data.items.length === 0 && (
        <p style={{ opacity: 0.7 }}>No rules configured yet.</p>
      )}

      <ul style={{ listStyle: 'none', padding: 0, display: 'grid', gap: 10 }}>
        {data?.items.map((r) => (
          <li
            key={r.id}
            style={{
              border: '1px solid #e5e7eb',
              borderRadius: 10,
              padding: 14,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <strong>{r.name}</strong>
              <span
                style={{
                  fontSize: 11,
                  padding: '2px 8px',
                  borderRadius: 999,
                  background: r.enabled ? '#dcfce7' : '#f3f4f6',
                  color: r.enabled ? '#166534' : '#374151',
                  fontWeight: 600,
                }}
              >
                {r.enabled ? 'enabled' : 'disabled'}
              </span>
              <span style={{ marginLeft: 'auto', fontSize: 11, color: '#6b7280' }}>
                on {r.trigger}
              </span>
            </div>

            {r.conditions.length > 0 && (
              <div style={{ marginTop: 8, fontSize: 13, color: '#374151' }}>
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
            <div style={{ marginTop: 4, fontSize: 13, color: '#374151' }}>
              <strong>THEN</strong>{' '}
              {r.actions.map((a, i) => (
                <span key={i}>
                  {i > 0 && ', '}
                  <code>{a.name}</code>
                  {a.params && Object.keys(a.params).length > 0 && (
                    <span style={{ opacity: 0.7 }}>
                      ({JSON.stringify(a.params)})
                    </span>
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
