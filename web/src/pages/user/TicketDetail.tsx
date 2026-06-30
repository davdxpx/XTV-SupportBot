import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { ConfirmDialog } from '@/components/ConfirmDialog';

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
  const [confirmClose, setConfirmClose] = useState(false);

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
    onSettled: () => setConfirmClose(false),
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
    <div style={{ display: 'flex', flexDirection: 'column', gap: 32 }}>
      <header style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <Link to="/tickets" style={{ fontSize: 13, fontFamily: 'IBM Plex Mono, monospace', color: 'var(--tg-text-dim)', textTransform: 'uppercase', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square">
            <line x1="19" y1="12" x2="5" y2="12"></line>
            <polyline points="12 19 5 12 12 5"></polyline>
          </svg>
          RETURN TO LIST
        </Link>
        <div>
          <h2 style={{ margin: 0, fontSize: 20, fontWeight: 600 }}>{data.subject || 'UNTITLED REQUEST'}</h2>
          <div style={{ fontSize: 11, fontFamily: 'IBM Plex Mono, monospace', color: 'var(--tg-text-dim)', textTransform: 'uppercase', marginTop: 8 }}>
            <span style={{ color: isOpen ? 'var(--tg-success)' : 'var(--tg-text-dim)', fontWeight: isOpen ? 600 : 400 }}>{data.status}</span>
            <span style={{ margin: '0 8px' }}>/</span>
            {data.priority ?? 'NORMAL'}
            <span style={{ margin: '0 8px' }}>/</span>
            {data.created_at ? new Date(data.created_at).toISOString().replace('T', ' ').slice(0, 16) : '—'}
          </div>
        </div>
      </header>

      <div className="thread">
        {data.history.map((h, i) => (
          <TapeNode key={i} entry={h} />
        ))}
      </div>

      {isOpen ? (
        <section style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <label className="label">REPLY</label>
            <textarea
              className="textarea"
              rows={4}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Enter your response here..."
              style={{ marginTop: 8 }}
            />
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              type="button"
              onClick={() => reply.mutate()}
              disabled={!draft.trim() || reply.isPending}
              className="btn btn-primary"
              style={{ flex: 1, padding: '14px', fontSize: 14 }}
            >
              {reply.isPending && <span className="spinner" />}
              {reply.isPending ? 'TRANSMITTING...' : 'SEND MESSAGE'}
            </button>
            <button
              type="button"
              onClick={() => setConfirmClose(true)}
              disabled={close.isPending}
              className="btn btn-ghost"
              style={{ color: 'var(--tg-danger)', borderColor: 'var(--tg-danger)', padding: '14px 20px', clipPath: 'polygon(0 0, 100% 0, 100% calc(100% - 8px), calc(100% - 8px) 100%, 0 100%)' }}
            >
              RESOLVE
            </button>
          </div>
        </section>
      ) : (
        <div style={{ padding: 24, textAlign: 'center', border: '1px dashed var(--tg-border)' }}>
          <span style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: 12, color: 'var(--tg-text-dim)', textTransform: 'uppercase' }}>
            RECORD RESOLVED AND LOCKED
          </span>
        </div>
      )}

      <ConfirmDialog
        open={confirmClose}
        danger
        title="Resolve this ticket?"
        body="Marking it resolved closes the request. You can always open a new one."
        confirmLabel="RESOLVE"
        busy={close.isPending}
        onConfirm={() => close.mutate()}
        onCancel={() => setConfirmClose(false)}
      />
    </div>
  );
}

function TapeNode({ entry }: { entry: HistoryEntry }) {
  const fromUser = entry.sender === 'user';
  return (
    <div className={`tape-msg ${fromUser ? 'user' : 'agent'}`}>
      <div className="tape-meta">
        <span style={{ color: fromUser ? 'var(--tg-text)' : 'var(--tg-accent)', fontWeight: 600 }}>
          {fromUser ? 'YOU' : 'SUPPORT'}
        </span>
        {entry.timestamp && (
          <span>{new Date(entry.timestamp).toISOString().replace('T', ' ').slice(0, 16)}</span>
        )}
      </div>
      <div className="tape-content">{entry.text}</div>
    </div>
  );
}
