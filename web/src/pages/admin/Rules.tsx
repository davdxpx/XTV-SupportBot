import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { ConfirmDialog } from '@/components/ConfirmDialog';

type Condition = { field: string; op: string; value: unknown };
type Action = { name: string; params?: Record<string, unknown> };

interface Rule {
  id: string;
  name: string;
  trigger: string;
  conditions: Condition[];
  actions: Action[];
  cooldown_s: number;
  enabled: boolean;
}

interface RulesResponse {
  items: Rule[];
  count: number;
}

const TRIGGERS = [
  'TicketCreated',
  'TicketClosed',
  'TicketReopened',
  'TicketAssigned',
  'TicketTagged',
  'TicketPriorityChanged',
  'MessagePosted',
  'SlaBreached',
];
const CONDITION_FIELDS = ['status', 'priority', 'tags', 'project_id', 'team_id', 'assignee_id'];
const CONDITION_OPS = ['eq', 'ne', 'in', 'not_in', 'contains'];
const ACTION_NAMES = [
  'assign',
  'tag',
  'untag',
  'set_priority',
  'reopen',
  'close',
  'notify_users',
  'ai_draft',
  'auto_reply',
  'webhook',
];

export function Rules() {
  const qc = useQueryClient();
  const [showBuilder, setShowBuilder] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<Rule | null>(null);

  const { data, isError, error: queryError } = useQuery({
    queryKey: ['admin-rules'],
    queryFn: () => api<RulesResponse>('/api/v1/rules'),
  });

  const toggleMut = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      api(`/api/v1/rules/${id}/enabled`, {
        method: 'PATCH',
        body: JSON.stringify({ enabled }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-rules'] }),
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => api(`/api/v1/rules/${id}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-rules'] }),
    onSettled: () => setPendingDelete(null),
  });

  if (isError) {
    const isForbidden = String(queryError).includes('403') || String(queryError).includes('insufficient_scope');
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
        <h1 className="heading">AUTOMATION LOGIC</h1>
        <div style={{ padding: 12, border: '1px solid var(--tg-danger)', background: 'var(--tg-danger-soft)', color: 'var(--tg-text)', fontSize: 13, fontFamily: 'IBM Plex Mono, monospace' }}>
          ERROR: {isForbidden ? 'INSUFFICIENT PERMISSIONS (rules:read)' : String(queryError)}
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div className="heading-row" style={{ marginBottom: 0, paddingBottom: 0, borderBottom: 'none' }}>
        <div>
          <h1 className="heading">AUTOMATION LOGIC</h1>
        </div>
        <button type="button" onClick={() => setShowBuilder(true)} className="btn btn-primary">
          DEFINE NEW LOGIC
        </button>
      </div>

      {showBuilder && <RuleBuilder onClose={() => setShowBuilder(false)} />}

      <ConfirmDialog
        open={!!pendingDelete}
        danger
        title="Purge rule?"
        body={
          <>
            This permanently deletes <strong>{pendingDelete?.name}</strong>. This cannot be undone.
          </>
        }
        confirmLabel="PURGE"
        busy={deleteMut.isPending}
        onConfirm={() => pendingDelete && deleteMut.mutate(pendingDelete.id)}
        onCancel={() => setPendingDelete(null)}
      />

      <ul className="ticket-list">
        {data?.items.map((r) => (
          <li key={r.id} className="ticket-item" style={{ display: 'flex', flexDirection: 'column', gap: 12, borderLeftColor: r.enabled ? 'var(--tg-accent)' : 'var(--tg-border)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <strong style={{ fontSize: 15 }}>{r.name}</strong>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <span className="mono" style={{ color: 'var(--tg-text-dim)', fontSize: 12 }}>ON {r.trigger.toUpperCase()}</span>
                <span style={{
                  fontSize: 10, fontFamily: 'IBM Plex Mono, monospace',
                  padding: '2px 6px', background: r.enabled ? 'var(--tg-success)' : 'var(--tg-surface-hi)', color: r.enabled ? 'var(--tg-bg)' : 'var(--tg-text-dim)'
                }}>
                  {r.enabled ? 'ENABLED' : 'DISABLED'}
                </span>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 4, fontFamily: 'IBM Plex Mono, monospace', fontSize: 12 }}>
              {r.conditions.length > 0 && (
                <div>
                  <span style={{ color: 'var(--tg-text-dim)', width: 40, display: 'inline-block' }}>IF</span>
                  {r.conditions.map((c, i) => (
                    <span key={i}>
                      {i > 0 && <span style={{ color: 'var(--tg-text-dim)' }}> AND </span>}
                      <span style={{ background: 'var(--tg-surface-hi)', padding: '2px 4px', border: '1px solid var(--tg-border)' }}>
                        {c.field} {c.op} {JSON.stringify(c.value)}
                      </span>
                    </span>
                  ))}
                </div>
              )}
              <div>
                <span style={{ color: 'var(--tg-accent)', width: 40, display: 'inline-block', fontWeight: 600 }}>THEN</span>
                {r.actions.map((a, i) => (
                  <span key={i}>
                    {i > 0 && <span style={{ color: 'var(--tg-text-dim)' }}> AND </span>}
                    <span style={{ background: 'var(--tg-accent-soft)', padding: '2px 4px', border: '1px solid var(--tg-accent)', color: 'var(--tg-accent)' }}>
                      {a.name.toUpperCase()}
                    </span>
                    {a.params && Object.keys(a.params).length > 0 && (
                      <span style={{ color: 'var(--tg-text-dim)', marginLeft: 4 }}>({JSON.stringify(a.params)})</span>
                    )}
                  </span>
                ))}
              </div>
            </div>

            <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
              <button
                type="button"
                onClick={() => toggleMut.mutate({ id: r.id, enabled: !r.enabled })}
                className="btn btn-ghost btn-sm"
              >
                {r.enabled ? 'DISABLE' : 'ENABLE'}
              </button>
              <button
                type="button"
                onClick={() => setPendingDelete(r)}
                className="btn btn-ghost btn-sm"
                style={{ color: 'var(--tg-danger)', borderColor: 'var(--tg-danger)', clipPath: 'polygon(0 0, 100% 0, 100% calc(100% - 6px), calc(100% - 6px) 100%, 0 100%)' }}
              >
                PURGE
              </button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function RuleBuilder({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [name, setName] = useState('');
  const [trigger, setTrigger] = useState(TRIGGERS[0]);
  const [conditions, setConditions] = useState<Condition[]>([]);
  const [actions, setActions] = useState<Action[]>([]);
  const [cooldown, setCooldown] = useState(0);
  const [enabled, setEnabled] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: () =>
      api('/api/v1/rules', {
        method: 'POST',
        body: JSON.stringify({
          name: name.trim(),
          trigger,
          conditions,
          actions,
          cooldown_s: cooldown,
          enabled,
        }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin-rules'] });
      onClose();
    },
    onError: (e) => setError(String(e)),
  });

  const canSave = !!name.trim() && actions.length > 0 && !create.isPending;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()} style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
        <h2 style={{ margin: 0, fontSize: 20, fontWeight: 600 }}>DEFINE LOGIC</h2>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <label className="label">RULE NAME</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Escalate billing tickets"
              className="input"
            />
          </div>

          <div>
            <label className="label">TRIGGER (EVENT)</label>
            <select
              value={trigger}
              onChange={(e) => setTrigger(e.target.value)}
              className="select"
            >
              {TRIGGERS.map((t) => (
                <option key={t} value={t}>
                  {t.toUpperCase()}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="label">CONDITIONS (OPTIONAL)</label>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {conditions.map((c, i) => (
                <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <select
                    value={c.field}
                    onChange={(e) =>
                      setConditions(conditions.map((x, j) =>
                        j === i ? { ...x, field: e.target.value } : x,
                      ))
                    }
                    className="select"
                    style={{ flex: 1 }}
                  >
                    {CONDITION_FIELDS.map((f) => (
                      <option key={f} value={f}>
                        {f}
                      </option>
                    ))}
                  </select>
                  <select
                    value={c.op}
                    onChange={(e) =>
                      setConditions(conditions.map((x, j) =>
                        j === i ? { ...x, op: e.target.value } : x,
                      ))
                    }
                    className="select"
                    style={{ width: 80, fontFamily: 'IBM Plex Mono, monospace' }}
                  >
                    {CONDITION_OPS.map((o) => (
                      <option key={o} value={o}>
                        {o}
                      </option>
                    ))}
                  </select>
                  <input
                    type="text"
                    value={String(c.value ?? '')}
                    onChange={(e) =>
                      setConditions(conditions.map((x, j) =>
                        j === i ? { ...x, value: e.target.value } : x,
                      ))
                    }
                    placeholder="value"
                    className="input"
                    style={{ flex: 1, fontFamily: 'IBM Plex Mono, monospace' }}
                  />
                  <button
                    type="button"
                    onClick={() =>
                      setConditions(conditions.filter((_, j) => j !== i))
                    }
                    className="btn btn-ghost btn-icon"
                    style={{ color: 'var(--tg-danger)', borderColor: 'var(--tg-danger)' }}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <line x1="18" y1="6" x2="6" y2="18"></line>
                      <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                  </button>
                </div>
              ))}
              <button
                type="button"
                onClick={() =>
                  setConditions([
                    ...conditions,
                    { field: CONDITION_FIELDS[0], op: 'eq', value: '' },
                  ])
                }
                className="btn btn-ghost btn-sm"
                style={{ alignSelf: 'flex-start' }}
              >
                + ADD CONDITION
              </button>
            </div>
          </div>

          <div>
            <label className="label">
              ACTIONS <span style={{ color: 'var(--tg-accent)' }}>*</span>
            </label>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {actions.map((a, i) => (
                <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <select
                    value={a.name}
                    onChange={(e) =>
                      setActions(actions.map((x, j) =>
                        j === i ? { ...x, name: e.target.value } : x,
                      ))
                    }
                    className="select"
                    style={{ flex: 1 }}
                  >
                    {ACTION_NAMES.map((n) => (
                      <option key={n} value={n}>
                        {n.toUpperCase()}
                      </option>
                    ))}
                  </select>
                  <input
                    type="text"
                    placeholder='{"key": "value"}'
                    value={JSON.stringify(a.params ?? {})}
                    onChange={(e) => {
                      try {
                        const parsed = JSON.parse(e.target.value || '{}');
                        setActions(actions.map((x, j) =>
                          j === i ? { ...x, params: parsed } : x,
                        ));
                      } catch {
                        // user still typing
                      }
                    }}
                    className="input"
                    style={{ flex: 2, fontFamily: 'IBM Plex Mono, monospace' }}
                  />
                  <button
                    type="button"
                    onClick={() => setActions(actions.filter((_, j) => j !== i))}
                    className="btn btn-ghost btn-icon"
                    style={{ color: 'var(--tg-danger)', borderColor: 'var(--tg-danger)' }}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <line x1="18" y1="6" x2="6" y2="18"></line>
                      <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                  </button>
                </div>
              ))}
              <button
                type="button"
                onClick={() =>
                  setActions([...actions, { name: ACTION_NAMES[0], params: {} }])
                }
                className="btn btn-ghost btn-sm"
                style={{ alignSelf: 'flex-start' }}
              >
                + ADD ACTION
              </button>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={enabled}
              onChange={(e) => setEnabled(e.target.checked)}
              style={{ accentColor: 'var(--tg-accent)', width: 16, height: 16 }}
            />
            <span style={{ fontSize: 13, fontFamily: 'IBM Plex Mono, monospace' }}>ENABLE ON SAVE</span>
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 11, fontFamily: 'IBM Plex Mono, monospace', color: 'var(--tg-text-dim)' }}>COOLDOWN (S)</span>
            <input
              type="number"
              min={0}
              value={cooldown}
              onChange={(e) => setCooldown(Number(e.target.value) || 0)}
              className="input"
              style={{ width: 80, fontFamily: 'IBM Plex Mono, monospace', padding: '6px 8px' }}
            />
          </label>
        </div>

        {error && (
          <div style={{ padding: 12, border: '1px solid var(--tg-danger)', background: 'var(--tg-danger-soft)', color: 'var(--tg-text)', fontSize: 13, fontFamily: 'IBM Plex Mono, monospace' }}>
            ERROR: {error}
          </div>
        )}

        <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
          <button
            type="button"
            onClick={() => create.mutate()}
            disabled={!canSave}
            className="btn btn-primary"
            style={{ flex: 1, padding: '14px', fontSize: 14 }}
          >
            {create.isPending ? 'COMMITING...' : 'COMMIT LOGIC'}
          </button>
          <button type="button" onClick={onClose} className="btn btn-ghost" style={{ padding: '14px 20px' }}>
            ABORT
          </button>
        </div>
      </div>
    </div>
  );
}
