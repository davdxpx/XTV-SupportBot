import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';

interface HistoryEntry {
  sender: string;
  text: string;
  timestamp: string | null;
  type: string;
}

interface AdminTicket {
  _id: string;
  user_id: number;
  status: string;
  priority?: string;
  tags?: string[];
  assignee_id?: number | null;
  project_id?: string | null;
  created_at?: string;
  closed_at?: string | null;
  message?: string;
  history?: HistoryEntry[];
}

export function AdminTicketDetail() {
  const { ticketId } = useParams<{ ticketId: string }>();
  const qc = useQueryClient();
  const [reply, setReply] = useState('');
  const [tagInput, setTagInput] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['admin-ticket', ticketId],
    queryFn: () => api<AdminTicket>(`/api/v1/tickets/${ticketId}`),
    enabled: !!ticketId,
  });

  const post = (path: string, body?: unknown) =>
    api(path, {
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    });

  const replyMut = useMutation({
    mutationFn: () => post(`/api/v1/tickets/${ticketId}/reply`, { message: reply.trim() }),
    onSuccess: () => {
      setReply('');
      qc.invalidateQueries({ queryKey: ['admin-ticket', ticketId] });
    },
  });
  const closeMut = useMutation({
    mutationFn: () => post(`/api/v1/tickets/${ticketId}/close`, { reason: 'resolved' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-ticket', ticketId] }),
  });
  const reopenMut = useMutation({
    mutationFn: () => post(`/api/v1/tickets/${ticketId}/reopen`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-ticket', ticketId] }),
  });
  const addTagMut = useMutation({
    mutationFn: (tag: string) =>
      api(`/api/v1/tickets/${ticketId}/tags`, {
        method: 'POST',
        body: JSON.stringify({ tags: [...(data?.tags ?? []), tag] }),
      }),
    onSuccess: () => {
      setTagInput('');
      qc.invalidateQueries({ queryKey: ['admin-ticket', ticketId] });
    },
  });

  if (isLoading) return <p>Loading ticket…</p>;
  if (!data) return <p>Not found.</p>;

  const isOpen = data.status === 'open';

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 24 }}>
      <div>
        <Link to="/admin/inbox" style={{ color: '#2563eb' }}>
          ← Inbox
        </Link>
        <h1 style={{ marginTop: 8 }}>
          Ticket #{data._id.slice(-6)} · {data.status}
        </h1>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {(data.history ?? []).map((h, i) => (
            <HistoryBubble key={i} entry={h} />
          ))}
        </div>

        {isOpen ? (
          <section style={{ marginTop: 16 }}>
            <textarea
              rows={4}
              value={reply}
              onChange={(e) => setReply(e.target.value)}
              placeholder="Agent reply…"
              style={{
                width: '100%',
                padding: 10,
                border: '1px solid #e5e7eb',
                borderRadius: 8,
                fontFamily: 'inherit',
                fontSize: 14,
              }}
            />
            <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
              <button
                type="button"
                disabled={!reply.trim() || replyMut.isPending}
                onClick={() => replyMut.mutate()}
                style={btn('#2563eb', '#fff')}
              >
                {replyMut.isPending ? 'Sending…' : 'Send reply'}
              </button>
              <button
                type="button"
                disabled={closeMut.isPending}
                onClick={() => closeMut.mutate()}
                style={btn('#fff', '#991b1b', '#fca5a5')}
              >
                Close
              </button>
            </div>
          </section>
        ) : (
          <section style={{ marginTop: 16 }}>
            <button
              type="button"
              onClick={() => reopenMut.mutate()}
              style={btn('#2563eb', '#fff')}
            >
              Reopen
            </button>
          </section>
        )}
      </div>

      <aside style={{ borderLeft: '1px solid #e5e7eb', paddingLeft: 16 }}>
        <h3>Meta</h3>
        <dl style={{ fontSize: 13 }}>
          <DItem k="User ID" v={String(data.user_id)} />
          <DItem k="Priority" v={data.priority ?? '—'} />
          <DItem k="Assignee" v={data.assignee_id ? String(data.assignee_id) : '—'} />
          <DItem
            k="Created"
            v={data.created_at ? new Date(data.created_at).toLocaleString() : '—'}
          />
          {data.closed_at && (
            <DItem k="Closed" v={new Date(data.closed_at).toLocaleString()} />
          )}
        </dl>

        <h3 style={{ marginTop: 20 }}>Tags</h3>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
          {(data.tags ?? []).map((tag) => (
            <span
              key={tag}
              style={{
                background: '#f3f4f6',
                padding: '2px 8px',
                borderRadius: 6,
                fontSize: 12,
              }}
            >
              #{tag}
            </span>
          ))}
        </div>
        <div style={{ marginTop: 6, display: 'flex', gap: 4 }}>
          <input
            type="text"
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            placeholder="add tag"
            style={{
              flex: 1,
              padding: 6,
              border: '1px solid #e5e7eb',
              borderRadius: 6,
              fontSize: 12,
            }}
          />
          <button
            type="button"
            disabled={!tagInput.trim() || addTagMut.isPending}
            onClick={() => addTagMut.mutate(tagInput.trim())}
            style={btn('#2563eb', '#fff')}
          >
            Add
          </button>
        </div>
      </aside>
    </div>
  );
}

function HistoryBubble({ entry }: { entry: HistoryEntry }) {
  const fromAgent = entry.sender === 'admin' || entry.sender === 'agent';
  return (
    <div
      style={{
        alignSelf: fromAgent ? 'flex-end' : 'flex-start',
        background: fromAgent ? '#eff6ff' : '#f3f4f6',
        padding: '8px 12px',
        borderRadius: 10,
        maxWidth: '80%',
      }}
    >
      <div
        style={{
          fontSize: 11,
          color: '#6b7280',
          marginBottom: 4,
          fontWeight: 600,
          textTransform: 'uppercase',
        }}
      >
        {entry.sender}
      </div>
      <div style={{ whiteSpace: 'pre-wrap', fontSize: 14 }}>{entry.text}</div>
      {entry.timestamp && (
        <div style={{ marginTop: 4, fontSize: 10, color: '#9ca3af' }}>
          {new Date(entry.timestamp).toLocaleString()}
        </div>
      )}
    </div>
  );
}

function DItem({ k, v }: { k: string; v: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0' }}>
      <dt style={{ color: '#6b7280' }}>{k}</dt>
      <dd style={{ margin: 0, fontFamily: 'ui-monospace, monospace' }}>{v}</dd>
    </div>
  );
}

function btn(bg: string, fg: string, border?: string): React.CSSProperties {
  return {
    padding: '8px 14px',
    background: bg,
    color: fg,
    border: border ? `1px solid ${border}` : 'none',
    borderRadius: 8,
    cursor: 'pointer',
    fontSize: 13,
  };
}
