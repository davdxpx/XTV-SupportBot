import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';

interface HistoryEntry {
  sender: 'user' | 'admin' | string;
  text: string;
  type: string;
  timestamp: string | null;
}

interface TicketDetail {
  id: string;
  status: string;
  priority?: string | null;
  tags?: string[];
  subject: string;
  created_at: string | null;
  closed_at: string | null;
  history: HistoryEntry[];
}

export function TicketDetail() {
  const { ticketId } = useParams<{ ticketId: string }>();
  const qc = useQueryClient();
  const [draft, setDraft] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['me-ticket', ticketId],
    queryFn: () => api<TicketDetail>(`/api/v1/me/tickets/${ticketId}`),
    enabled: !!ticketId,
  });

  const reply = useMutation({
    mutationFn: () =>
      api(`/api/v1/me/tickets/${ticketId}/reply`, {
        method: 'POST',
        body: JSON.stringify({ message: draft.trim() }),
      }),
    onSuccess: () => {
      setDraft('');
      qc.invalidateQueries({ queryKey: ['me-ticket', ticketId] });
      qc.invalidateQueries({ queryKey: ['my-tickets'] });
    },
  });

  const close = useMutation({
    mutationFn: () =>
      api(`/api/v1/me/tickets/${ticketId}/close`, {
        method: 'POST',
        body: JSON.stringify({ reason: 'resolved_by_user' }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['me-ticket', ticketId] });
      qc.invalidateQueries({ queryKey: ['my-tickets'] });
    },
  });

  if (isLoading) {
    return (
      <div className="stack">
        <span className="skeleton skeleton-line" style={{ width: '30%' }} />
        <span className="skeleton skeleton-line" style={{ width: '60%' }} />
        <div className="skeleton skeleton-block" />
        <div className="skeleton skeleton-block" />
      </div>
    );
  }
  if (!data) return <p className="muted">Ticket not found.</p>;

  const isOpen = data.status === 'open';

  return (
    <div className="stack stack-lg">
      <Link to="/tickets" className="muted" style={{ fontSize: 14 }}>
        ← Back to tickets
      </Link>
      <header className="stack" style={{ gap: 4 }}>
        <h2 style={{ margin: 0 }}>{data.subject || 'Ticket'}</h2>
        <div className="muted" style={{ fontSize: 12 }}>
          {data.status} · {data.priority ?? 'normal'} ·{' '}
          {data.created_at ? new Date(data.created_at).toLocaleString() : '—'}
        </div>
      </header>

      <div className="thread">
        {data.history.map((h, i) => (
          <Bubble key={i} entry={h} />
        ))}
      </div>

      {isOpen ? (
        <section className="stack">
          <textarea
            className="textarea"
            rows={4}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Write a reply…"
          />
          <div className="row">
            <button
              type="button"
              onClick={() => reply.mutate()}
              disabled={!draft.trim() || reply.isPending}
              className="btn btn-primary"
              style={{ flex: 1 }}
            >
              {reply.isPending && <span className="spinner" />}
              {reply.isPending ? 'Sending…' : 'Send reply'}
            </button>
            <button
              type="button"
              onClick={() => {
                if (confirm('Close this ticket?')) close.mutate();
              }}
              disabled={close.isPending}
              className="btn btn-danger"
            >
              Close
            </button>
          </div>
        </section>
      ) : (
        <div className="card muted" style={{ textAlign: 'center' }}>
          This ticket is closed.
        </div>
      )}
    </div>
  );
}

function Bubble({ entry }: { entry: HistoryEntry }) {
  const fromUser = entry.sender === 'user';
  return (
    <div className={`bubble ${fromUser ? 'bubble-user' : 'bubble-agent'}`}>
      <div style={{ whiteSpace: 'pre-wrap' }}>{entry.text}</div>
      {entry.timestamp && (
        <div className="bubble-time">{new Date(entry.timestamp).toLocaleString()}</div>
      )}
    </div>
  );
}
