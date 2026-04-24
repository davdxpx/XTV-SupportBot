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

  if (isLoading) return <p>Loading ticket…</p>;
  if (!data) return <p>Ticket not found.</p>;

  const isOpen = data.status === 'open';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <Link to="/tickets" style={{ color: '#2563eb', fontSize: 14 }}>
        ← Back to tickets
      </Link>
      <header>
        <h2 style={{ margin: '4px 0 6px' }}>{data.subject || 'Ticket'}</h2>
        <div style={{ fontSize: 12, opacity: 0.7 }}>
          {data.status} · {data.priority ?? 'normal'} ·{' '}
          {data.created_at
            ? new Date(data.created_at).toLocaleString()
            : '—'}
        </div>
      </header>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {data.history.map((h, i) => (
          <Bubble key={i} entry={h} />
        ))}
      </div>

      {isOpen ? (
        <section style={{ marginTop: 8 }}>
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            rows={4}
            placeholder="Write a reply…"
            style={{
              width: '100%',
              padding: 10,
              border: '1px solid #e5e7eb',
              borderRadius: 10,
              fontFamily: 'inherit',
              fontSize: 15,
              resize: 'vertical',
            }}
          />
          <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
            <button
              type="button"
              onClick={() => reply.mutate()}
              disabled={!draft.trim() || reply.isPending}
              style={{
                padding: '10px 18px',
                background: '#2563eb',
                color: '#ffffff',
                border: 'none',
                borderRadius: 10,
                cursor: 'pointer',
                flex: 1,
              }}
            >
              {reply.isPending ? 'Sending…' : 'Send reply'}
            </button>
            <button
              type="button"
              onClick={() => {
                if (confirm('Close this ticket?')) close.mutate();
              }}
              disabled={close.isPending}
              style={{
                padding: '10px 14px',
                background: 'transparent',
                color: '#991b1b',
                border: '1px solid #fca5a5',
                borderRadius: 10,
                cursor: 'pointer',
              }}
            >
              Close
            </button>
          </div>
        </section>
      ) : (
        <div
          style={{
            padding: 12,
            background: '#f3f4f6',
            color: '#374151',
            borderRadius: 10,
            fontSize: 13,
            textAlign: 'center',
          }}
        >
          This ticket is closed.
        </div>
      )}
    </div>
  );
}

function Bubble({ entry }: { entry: HistoryEntry }) {
  const fromUser = entry.sender === 'user';
  return (
    <div
      style={{
        alignSelf: fromUser ? 'flex-end' : 'flex-start',
        maxWidth: '85%',
        background: fromUser ? '#2563eb' : '#f3f4f6',
        color: fromUser ? '#ffffff' : '#111827',
        padding: '8px 12px',
        borderRadius: 12,
        borderBottomRightRadius: fromUser ? 2 : 12,
        borderBottomLeftRadius: fromUser ? 12 : 2,
      }}
    >
      <div style={{ whiteSpace: 'pre-wrap', fontSize: 14 }}>{entry.text}</div>
      {entry.timestamp && (
        <div
          style={{
            marginTop: 4,
            fontSize: 10,
            opacity: 0.7,
            textAlign: 'right',
          }}
        >
          {new Date(entry.timestamp).toLocaleString()}
        </div>
      )}
    </div>
  );
}
