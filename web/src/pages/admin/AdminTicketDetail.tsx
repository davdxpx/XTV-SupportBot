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
    mutationFn: () =>
      post(`/api/v1/tickets/${ticketId}/reply`, { message: reply.trim() }),
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

  if (isLoading) return <p className="muted">Loading ticket…</p>;
  if (!data) return <p className="muted">Not found.</p>;

  const isOpen = data.status === 'open';

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 28 }}>
      <div className="stack">
        <Link to="/admin/inbox" className="muted">← Inbox</Link>
        <h1 className="heading">
          Ticket #{data._id.slice(-6)} · {data.status}
        </h1>

        <div className="thread">
          {(data.history ?? []).map((h, i) => (
            <HistoryBubble key={i} entry={h} />
          ))}
        </div>

        {isOpen ? (
          <section className="stack">
            <textarea
              rows={4}
              value={reply}
              onChange={(e) => setReply(e.target.value)}
              placeholder="Agent reply…"
              className="textarea"
            />
            <div className="row">
              <button
                type="button"
                disabled={!reply.trim() || replyMut.isPending}
                onClick={() => replyMut.mutate()}
                className="btn btn-primary"
              >
                {replyMut.isPending ? 'Sending…' : 'Send reply'}
              </button>
              <button
                type="button"
                disabled={closeMut.isPending}
                onClick={() => closeMut.mutate()}
                className="btn btn-danger"
              >
                Close
              </button>
            </div>
          </section>
        ) : (
          <section>
            <button
              type="button"
              onClick={() => reopenMut.mutate()}
              className="btn btn-primary"
            >
              Reopen
            </button>
          </section>
        )}
      </div>

      <aside className="card stack">
        <h3 style={{ margin: 0 }}>Meta</h3>
        <dl className="stack" style={{ margin: 0, gap: 4, fontSize: 13 }}>
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

        <h3 style={{ margin: '10px 0 0' }}>Tags</h3>
        <div className="row" style={{ flexWrap: 'wrap', gap: 4 }}>
          {(data.tags ?? []).map((tag) => (
            <span key={tag} className="pill pill-muted">#{tag}</span>
          ))}
        </div>
        <div className="row" style={{ gap: 4 }}>
          <input
            type="text"
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            placeholder="add tag"
            className="input"
            style={{ padding: 8, fontSize: 13 }}
          />
          <button
            type="button"
            disabled={!tagInput.trim() || addTagMut.isPending}
            onClick={() => addTagMut.mutate(tagInput.trim())}
            className="btn btn-primary btn-sm"
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
    <div className={`bubble ${fromAgent ? 'bubble-user' : 'bubble-agent'}`}>
      <div className="muted" style={{ fontSize: 10, marginBottom: 4, fontWeight: 700, textTransform: 'uppercase', color: 'inherit', opacity: 0.7 }}>
        {entry.sender}
      </div>
      <div style={{ whiteSpace: 'pre-wrap' }}>{entry.text}</div>
      {entry.timestamp && (
        <div className="bubble-time">{new Date(entry.timestamp).toLocaleString()}</div>
      )}
    </div>
  );
}

function DItem({ k, v }: { k: string; v: string }) {
  return (
    <div className="row" style={{ justifyContent: 'space-between' }}>
      <dt className="muted">{k}</dt>
      <dd style={{ margin: 0, fontFamily: 'ui-monospace, monospace' }}>{v}</dd>
    </div>
  );
}
