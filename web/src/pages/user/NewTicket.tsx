import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, ApiError } from '@/lib/api';

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
  const [error, setError] = useState<string | null>(null);

  const projects = useQuery({
    queryKey: ['me-projects'],
    queryFn: () => api<ProjectsResponse>('/api/v1/me/projects'),
  });

  const submit = useMutation({
    mutationFn: () =>
      api<{ id: string }>('/api/v1/me/tickets', {
        method: 'POST',
        body: JSON.stringify({
          project_id: projectId,
          message: message.trim(),
        }),
      }),
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

  const canSubmit = message.trim().length > 0 && !submit.isPending;

  return (
    <div className="stack stack-lg">
      <h2 className="heading">📮 New ticket</h2>

      {projects.isLoading && <p className="muted">Loading projects…</p>}
      {projects.data && projects.data.items.length > 0 && (
        <section>
          <p className="section-title">Pick an area</p>
          <div className="tiles">
            {projects.data.items.map((p) => {
              const active = p.id === projectId;
              return (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => setProjectId(active ? null : p.id)}
                  className={`tile${active ? ' tile-active' : ''}`}
                >
                  <div className="tile-title">📂 {p.name}</div>
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
        <label className="label" htmlFor="new-msg">Your message</label>
        <textarea
          id="new-msg"
          className="textarea"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          rows={6}
          placeholder="Describe your issue — photo, voice note, or document works too."
        />
        <div className="muted" style={{ fontSize: 11, marginTop: 4 }}>
          {message.length} / 4000
        </div>
      </section>

      {error && (
        <div className="pill pill-danger" style={{ padding: 10 }}>
          {error}
        </div>
      )}

      <button
        type="button"
        onClick={() => submit.mutate()}
        disabled={!canSubmit}
        className="btn btn-primary"
      >
        {submit.isPending && <span className="spinner" />}
        {submit.isPending ? 'Sending…' : 'Send ticket'}
      </button>
    </div>
  );
}
