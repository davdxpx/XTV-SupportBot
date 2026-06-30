import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, ApiError, uploadMyTicketAttachment } from '@/lib/api';

interface ProjectsResponse {
  items: Array<{
    id: string;
    slug: string | null;
    name: string;
    description?: string | null;
    type?: string | null;
  }>;
}

export function NewTicket() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [projectId, setProjectId] = useState<string | null>(null);
  const [message, setMessage] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [error, setError] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  const projects = useQuery({
    queryKey: ['me-projects'],
    queryFn: () => api<ProjectsResponse>('/api/v1/me/projects'),
  });

  const submit = useMutation({
    mutationFn: async () => {
      const res = await api<{ id: string }>('/api/v1/me/tickets', {
        method: 'POST',
        body: JSON.stringify({ project_id: projectId, message: message.trim() }),
      });
      // Upload any attachments after the ticket exists (sequential — keeps
      // ordering and avoids hammering the bot client).
      for (const f of files) {
        await uploadMyTicketAttachment(res.id, f);
      }
      return res;
    },
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['my-tickets-home'] });
      qc.invalidateQueries({ queryKey: ['my-tickets'] });
      navigate(`/tickets/${res.id}`);
    },
    onError: (err) => {
      if (err instanceof ApiError) {
        setError(
          typeof err.body === 'object' && err.body !== null
            ? JSON.stringify(err.body)
            : `${err.status}`,
        );
      } else {
        setError(String(err));
      }
    },
  });

  const canSubmit = !!projectId && message.trim().length > 0 && !submit.isPending;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 32 }}>
      <header>
        <h2 style={{ margin: 0, fontSize: 24, fontWeight: 600, letterSpacing: '-0.02em' }}>NEW REQUEST</h2>
      </header>

      {projects.isLoading && (
        <div className="tiles">
          <div className="skeleton skeleton-block" />
          <div className="skeleton skeleton-block" />
        </div>
      )}
      {projects.isError && (
        <div style={{ padding: 12, border: '1px solid var(--tg-danger)', background: 'var(--tg-danger-soft)', color: 'var(--tg-text)', fontSize: 13, fontFamily: 'IBM Plex Mono, monospace' }}>
          ERROR: INTAKE_AREAS_UNREACHABLE
        </div>
      )}
      {projects.data && projects.data.items.length === 0 && (
        <div style={{ padding: 32, textAlign: 'center', border: '1px dashed var(--tg-border)' }}>
          <div style={{ color: 'var(--tg-text-dim)', fontFamily: 'IBM Plex Mono, monospace', textTransform: 'uppercase' }}>
            No intake areas available. Please contact an administrator.
          </div>
        </div>
      )}
      {projects.data && projects.data.items.length > 0 && (
        <section>
          <label className="label">
            ROUTING AREA <span style={{ color: 'var(--tg-accent)' }}>*</span>
          </label>
          <div className="tiles" style={{ marginTop: 8 }}>
            {projects.data.items.map((p) => {
              const active = p.id === projectId;
              return (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => setProjectId(active ? null : p.id)}
                  className={`tile${active ? ' tile-active' : ''}`}
                >
                  <div className="tile-title">{p.name}</div>
                  {p.description && (
                    <div className="tile-desc">{p.description.slice(0, 80)}</div>
                  )}
                </button>
              );
            })}
          </div>
        </section>
      )}

      <section>
        <label className="label" htmlFor="new-msg">INITIAL MESSAGE <span style={{ color: 'var(--tg-accent)' }}>*</span></label>
        <textarea
          id="new-msg"
          className="textarea"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          rows={6}
          placeholder="Describe the issue. Detailed information reduces resolution time."
          style={{ marginTop: 8 }}
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8 }}>
          <span style={{ fontSize: 11, fontFamily: 'IBM Plex Mono, monospace', color: 'var(--tg-text-dim)' }}>
            TEXT REQUIRED
          </span>
          <span style={{ fontSize: 11, fontFamily: 'IBM Plex Mono, monospace', color: 'var(--tg-text-dim)' }}>
            {message.length} / 4000
          </span>
        </div>
      </section>

      <section>
        <label className="label">ATTACHMENTS (OPTIONAL)</label>
        <input
          ref={fileInput}
          type="file"
          multiple
          accept="image/*,.pdf,.txt,.log,.zip"
          onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
          style={{ display: 'none' }}
        />
        <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 8 }}>
          <button type="button" onClick={() => fileInput.current?.click()} className="btn btn-ghost btn-sm" style={{ alignSelf: 'flex-start' }}>
            📎 ADD FILES
          </button>
          {files.map((f, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, fontFamily: 'IBM Plex Mono, monospace', color: 'var(--tg-text-dim)' }}>
              <span>{f.name} ({Math.round(f.size / 1024)} KB)</span>
              <button type="button" onClick={() => setFiles(files.filter((_, j) => j !== i))} style={{ background: 'none', border: 'none', color: 'var(--tg-danger)', cursor: 'pointer' }}>✕</button>
            </div>
          ))}
        </div>
      </section>

      {error && (
        <div style={{ padding: 12, border: '1px solid var(--tg-danger)', background: 'var(--tg-danger-soft)', color: 'var(--tg-text)', fontSize: 13, fontFamily: 'IBM Plex Mono, monospace' }}>
          {error}
        </div>
      )}

      <button
        type="button"
        onClick={() => submit.mutate()}
        disabled={!canSubmit}
        className="btn btn-primary"
        style={{ padding: '16px', fontSize: 16, width: '100%', marginTop: projectId ? 0 : 24 }}
      >
        {submit.isPending && <span className="spinner" />}
        {submit.isPending
          ? 'TRANSMITTING...'
          : !projectId
            ? 'SELECT AREA TO CONTINUE'
            : 'SUBMIT REQUEST'}
      </button>
    </div>
  );
}
