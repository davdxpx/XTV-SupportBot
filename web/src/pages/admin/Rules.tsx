import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';

interface Condition {
  field: string;
  op: string;
  value: unknown;
}

interface Action {
  name: string;
  params?: Record<string, unknown>;
}

interface Rule {
  id: string;
  name: string;
  enabled: boolean;
  trigger: string;
  conditions: Condition[];
  actions: Action[];
  cooldown_s?: number;
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
  'apply_macro',
  'close',
  'reopen',
  'add_internal_note',
  'emoji_react',
  'trigger_webhook',
];

export function Rules() {
  const qc = useQueryClient();
  const [showBuilder, setShowBuilder] = useState(false);

  const { data, isLoading } = useQuery({
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
  });

  return (
    <div className="stack stack-lg">
      <div className="heading-row">
        <h1 className="heading">Automation rules</h1>
        <button
          type="button"
          onClick={() => setShowBuilder(true)}
          className="btn btn-primary"
        >
          + New rule
        </button>
      </div>

      {showBuilder && <RuleBuilder onClose={() => setShowBuilder(false)} />}

      {isLoading && (
        <ul className="ticket-list">
          {[0, 1].map((i) => (
            <li key={i} className="card">
              <div className="skeleton skeleton-line" style={{ width: '30%' }} />
              <div className="skeleton skeleton-line" style={{ width: '70%' }} />
            </li>
          ))}
        </ul>
      )}
      {data && data.items.length === 0 && !isLoading && (
        <p className="muted">No rules configured yet. Click “New rule” to create one.</p>
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

            <div className="row" style={{ gap: 8 }}>
              <button
                type="button"
                onClick={() =>
                  toggleMut.mutate({ id: r.id, enabled: !r.enabled })
                }
                className="btn btn-ghost btn-sm"
              >
                {r.enabled ? 'Disable' : 'Enable'}
              </button>
              <button
                type="button"
                onClick={() => {
                  if (confirm(`Delete rule "${r.name}"?`)) deleteMut.mutate(r.id);
                }}
                className="btn btn-danger btn-sm"
              >
                Delete
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
      <div className="modal stack" onClick={(e) => e.stopPropagation()}>
        <h2 style={{ margin: 0 }}>New rule</h2>

        <div>
          <label className="label">Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Escalate billing tickets"
            className="input"
          />
        </div>

        <div>
          <label className="label">WHEN — trigger</label>
          <select
            value={trigger}
            onChange={(e) => setTrigger(e.target.value)}
            className="input"
          >
            {TRIGGERS.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="label">AND — conditions (optional)</label>
          <div className="stack" style={{ gap: 6 }}>
            {conditions.map((c, i) => (
              <div key={i} className="row" style={{ gap: 6 }}>
                <select
                  value={c.field}
                  onChange={(e) =>
                    setConditions(conditions.map((x, j) =>
                      j === i ? { ...x, field: e.target.value } : x,
                    ))
                  }
                  className="input"
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
                  className="input"
                  style={{ width: 90 }}
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
                  style={{ flex: 1 }}
                />
                <button
                  type="button"
                  onClick={() =>
                    setConditions(conditions.filter((_, j) => j !== i))
                  }
                  className="btn btn-ghost btn-sm"
                >
                  ×
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
            >
              + Add condition
            </button>
          </div>
        </div>

        <div>
          <label className="label">
            THEN — actions <span style={{ color: 'var(--tg-danger)' }}>*</span>
          </label>
          <div className="stack" style={{ gap: 6 }}>
            {actions.map((a, i) => (
              <div key={i} className="row" style={{ gap: 6 }}>
                <select
                  value={a.name}
                  onChange={(e) =>
                    setActions(actions.map((x, j) =>
                      j === i ? { ...x, name: e.target.value } : x,
                    ))
                  }
                  className="input"
                  style={{ flex: 1 }}
                >
                  {ACTION_NAMES.map((n) => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ))}
                </select>
                <input
                  type="text"
                  placeholder='params as JSON, e.g. {"tag":"vip"}'
                  value={JSON.stringify(a.params ?? {})}
                  onChange={(e) => {
                    try {
                      const parsed = JSON.parse(e.target.value || '{}');
                      setActions(actions.map((x, j) =>
                        j === i ? { ...x, params: parsed } : x,
                      ));
                    } catch {
                      /* ignore, user is still typing */
                    }
                  }}
                  className="input"
                  style={{ flex: 2 }}
                />
                <button
                  type="button"
                  onClick={() => setActions(actions.filter((_, j) => j !== i))}
                  className="btn btn-ghost btn-sm"
                >
                  ×
                </button>
              </div>
            ))}
            <button
              type="button"
              onClick={() =>
                setActions([...actions, { name: ACTION_NAMES[0], params: {} }])
              }
              className="btn btn-ghost btn-sm"
            >
              + Add action
            </button>
          </div>
        </div>

        <div className="row" style={{ gap: 16 }}>
          <label className="row" style={{ gap: 6 }}>
            <input
              type="checkbox"
              checked={enabled}
              onChange={(e) => setEnabled(e.target.checked)}
            />
            <span>Enabled on save</span>
          </label>
          <div style={{ flex: 1 }} />
          <label className="row" style={{ gap: 6 }}>
            <span className="muted">Cooldown (s):</span>
            <input
              type="number"
              min={0}
              value={cooldown}
              onChange={(e) => setCooldown(Number(e.target.value) || 0)}
              className="input"
              style={{ width: 100 }}
            />
          </label>
        </div>

        {error && <div className="pill pill-danger" style={{ padding: 10 }}>{error}</div>}

        <div className="row">
          <button
            type="button"
            onClick={() => create.mutate()}
            disabled={!canSave}
            className="btn btn-primary"
            style={{ flex: 1 }}
          >
            {create.isPending && <span className="spinner" />}
            {create.isPending ? 'Creating…' : 'Create rule'}
          </button>
          <button type="button" onClick={onClose} className="btn btn-ghost">
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
