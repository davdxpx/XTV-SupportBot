import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Attachment } from '@/components/Attachment';

interface HistoryEntry {
  sender: string;
  text: string;
  timestamp: string | null;
  type: string;
  file_id?: string | null;
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
  is_vip?: boolean;
  tier_label?: string | null;
  display_badge?: string | null;
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

  if (isLoading) return <div style={{ padding: 24, fontFamily: 'IBM Plex Mono, monospace', color: 'var(--tg-text-dim)' }}>LOADING...</div>;
  if (!data) return <div style={{ padding: 24, fontFamily: 'IBM Plex Mono, monospace', color: 'var(--tg-text-dim)' }}>RECORD NOT FOUND</div>;

  const isOpen = data.status === 'open';

  return (
    <div className="admin-detail-grid">
      <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
        <header style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <Link to="/admin/inbox" style={{ fontSize: 13, fontFamily: 'IBM Plex Mono, monospace', color: 'var(--tg-text-dim)', textTransform: 'uppercase', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square">
              <line x1="19" y1="12" x2="5" y2="12"></line>
              <polyline points="12 19 5 12 12 5"></polyline>
            </svg>
            RETURN TO QUEUE
          </Link>
          <div>
            <h1 className="heading" style={{ fontFamily: 'IBM Plex Mono, monospace' }}>
              RECORD <span style={{ color: 'var(--tg-accent)' }}>{data._id.slice(-6).toUpperCase()}</span>
            </h1>
          </div>
        </header>

        <div className="thread" style={{ marginBottom: 32 }}>
          {(data.history ?? []).map((h, i) => (
            <TapeNode key={i} entry={h} ticketId={data._id} index={i} />
          ))}
        </div>

        {isOpen ? (
          <section style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <label className="label">RESPONSE LOG</label>
            <textarea
              rows={5}
              value={reply}
              onChange={(e) => setReply(e.target.value)}
              placeholder="Enter resolution notes or client response..."
              className="textarea"
            />
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                type="button"
                disabled={!reply.trim() || replyMut.isPending}
                onClick={() => replyMut.mutate()}
                className="btn btn-primary"
                style={{ flex: 1 }}
              >
                {replyMut.isPending ? 'TRANSMITTING...' : 'DISPATCH'}
              </button>
              <button
                type="button"
                disabled={closeMut.isPending}
                onClick={() => closeMut.mutate()}
                className="btn btn-ghost"
                style={{ color: 'var(--tg-danger)', borderColor: 'var(--tg-danger)', padding: '10px 24px' }}
              >
                RESOLVE RECORD
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
              RE-OPEN RECORD
            </button>
          </section>
        )}
      </div>

      <aside className="sticky-panel">
        <p className="section-title">METADATA</p>
        <dl style={{ margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: 12 }}>
          <DItem k="USER ID" v={
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              {String(data.user_id)}
              {(data.is_vip || data.display_badge) && (
                <span style={{
                  fontSize: 10, fontFamily: 'IBM Plex Mono, monospace',
                  padding: '0 4px', background: 'var(--tg-accent-soft)', color: 'var(--tg-accent)', border: '1px solid var(--tg-accent)'
                }}>
                  {data.display_badge || data.tier_label || 'VIP'}
                </span>
              )}
            </div>
          } />
          <DItem k="STATUS" v={<span style={{ color: isOpen ? 'var(--tg-success)' : 'var(--tg-text-dim)' }}>{data.status.toUpperCase()}</span>} />
          <DItem k="PRIORITY" v={data.priority?.toUpperCase() ?? '--'} />
          <DItem k="ASSIGNEE" v={data.assignee_id ? String(data.assignee_id) : '--'} />
          <DItem
            k="CREATED"
            v={data.created_at ? new Date(data.created_at).toISOString().replace('T', ' ').slice(0, 16) : '--'}
          />
          {data.closed_at && (
            <DItem k="CLOSED" v={new Date(data.closed_at).toISOString().replace('T', ' ').slice(0, 16)} />
          )}
        </dl>

        <p className="section-title" style={{ marginTop: 24 }}>ROUTING TAGS</p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 12 }}>
          {(data.tags ?? []).map((tag) => (
            <span key={tag} style={{
              fontSize: 11, fontFamily: 'IBM Plex Mono, monospace',
              padding: '4px 8px', background: 'var(--tg-surface-hi)', color: 'var(--tg-text-dim)', border: '1px solid var(--tg-border)'
            }}>
              {tag}
            </span>
          ))}
          {(!data.tags || data.tags.length === 0) && (
            <span style={{ color: 'var(--tg-text-dim)', fontSize: 12, fontFamily: 'IBM Plex Mono, monospace' }}>NO TAGS</span>
          )}
        </div>
        <div style={{ display: 'flex', gap: 4 }}>
          <input
            type="text"
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            placeholder="ADD TAG"
            className="input"
            style={{ padding: '8px 12px', fontSize: 13, fontFamily: 'IBM Plex Mono, monospace' }}
          />
          <button
            type="button"
            disabled={!tagInput.trim() || addTagMut.isPending}
            onClick={() => addTagMut.mutate(tagInput.trim())}
            className="btn btn-ghost btn-sm"
          >
            +
          </button>
        </div>
      </aside>
    </div>
  );
}

function TapeNode({ entry, ticketId, index }: { entry: HistoryEntry; ticketId: string; index: number }) {
  const fromAgent = entry.sender === 'admin' || entry.sender === 'agent';
  return (
    <div className={`tape-msg ${fromAgent ? 'agent' : 'user'}`}>
      <div className="tape-meta">
        <span style={{ color: fromAgent ? 'var(--tg-accent)' : 'var(--tg-text)', fontWeight: 600 }}>
          {entry.sender.toUpperCase()}
        </span>
        {entry.timestamp && (
          <span>{new Date(entry.timestamp).toISOString().replace('T', ' ').slice(0, 16)}</span>
        )}
      </div>
      <div className="tape-content">{entry.text}</div>
      {entry.file_id && (
        <div style={{ marginTop: 8 }}>
          <Attachment
            path={`/api/v1/tickets/${ticketId}/attachments/${index}`}
            kind={entry.type === 'photo' ? 'photo' : 'document'}
          />
        </div>
      )}
    </div>
  );
}

function DItem({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <dt style={{ margin: 0, fontSize: 11, fontFamily: 'IBM Plex Mono, monospace', color: 'var(--tg-text-dim)' }}>{k}</dt>
      <dd style={{ margin: 0, fontSize: 13, fontFamily: 'IBM Plex Mono, monospace' }}>{v}</dd>
    </div>
  );
}
