import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
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
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <h2 style={{ margin: 0 }}>📮 New ticket</h2>

      {projects.isLoading && <p>Loading projects…</p>}
      {projects.data && projects.data.items.length > 0 && (
        <section>
          <div style={{ fontSize: 13, opacity: 0.7, marginBottom: 6 }}>
            Pick the area your question is about:
          </div>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(2, 1fr)',
              gap: 8,
            }}
          >
            {projects.data.items.map((p) => {
              const active = p.id === projectId;
              return (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => setProjectId(active ? null : p.id)}
                  style={{
                    padding: '12px 10px',
                    border: active
                      ? '2px solid #2563eb'
                      : '1px solid #e5e7eb',
                    background: active ? '#eff6ff' : 'transparent',
                    borderRadius: 10,
                    textAlign: 'left',
                    cursor: 'pointer',
                  }}
                >
                  <div style={{ fontWeight: 600 }}>📂 {p.name}</div>
                  {p.description && (
                    <div
                      style={{
                        fontSize: 12,
                        opacity: 0.7,
                        marginTop: 2,
                      }}
                    >
                      {p.description.slice(0, 80)}
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </section>
      )}

      <section>
        <label
          style={{ display: 'block', fontSize: 13, marginBottom: 6, opacity: 0.7 }}
        >
          Your message
        </label>
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          rows={6}
          placeholder="Describe your issue — we'll usually reply within 30 minutes during business hours."
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
        <div style={{ fontSize: 11, opacity: 0.6, marginTop: 4 }}>
          {message.length} / 4000
        </div>
      </section>

      {error && (
        <div
          style={{
            padding: 10,
            background: '#fee2e2',
            color: '#991b1b',
            borderRadius: 8,
            fontSize: 13,
          }}
        >
          {error}
        </div>
      )}

      <button
        type="button"
        onClick={() => submit.mutate()}
        disabled={!canSubmit}
        style={{
          padding: '14px 18px',
          background: canSubmit ? '#2563eb' : '#cbd5e1',
          color: '#ffffff',
          border: 'none',
          borderRadius: 12,
          fontSize: 16,
          fontWeight: 600,
          cursor: canSubmit ? 'pointer' : 'not-allowed',
        }}
      >
        {submit.isPending ? 'Sending…' : 'Send ticket'}
      </button>
    </div>
  );
}
