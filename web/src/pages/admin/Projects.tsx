import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';

interface Project {
  _id: string;
  slug?: string;
  name: string;
  description?: string;
  type?: string;
  active?: boolean;
  ticket_count?: number;
}

interface ProjectsResponse {
  items: Project[];
  count: number;
}

const TEMPLATES = [
  { slug: 'support', label: 'Tech support' },
  { slug: 'feedback', label: 'Feedback' },
  { slug: 'contact', label: 'Contact form' },
  { slug: 'billing', label: 'Billing' },
  { slug: 'dev_github', label: 'Dev (GitHub)' },
  { slug: 'vip', label: 'VIP' },
  { slug: 'community', label: 'Community' },
];

export function Projects() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);

  const { data, isError, error: queryError } = useQuery({
    queryKey: ['admin-projects'],
    queryFn: () => api<ProjectsResponse>('/api/v1/projects'),
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => api(`/api/v1/projects/${id}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-projects'] }),
  });

  if (isError) {
    const isForbidden = String(queryError).includes('403') || String(queryError).includes('insufficient_scope');
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
        <h1 className="heading">SYSTEM ARCHITECTURE</h1>
        <div style={{ padding: 12, border: '1px solid var(--tg-danger)', background: 'var(--tg-danger-soft)', color: 'var(--tg-text)', fontSize: 13, fontFamily: 'IBM Plex Mono, monospace' }}>
          ERROR: {isForbidden ? 'INSUFFICIENT PERMISSIONS (projects:read)' : String(queryError)}
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div className="heading-row" style={{ marginBottom: 0, paddingBottom: 0, borderBottom: 'none' }}>
        <div>
          <h1 className="heading">SYSTEM ARCHITECTURE</h1>
        </div>
        <button type="button" onClick={() => setShowCreate(true)} className="btn btn-primary">
          PROVISION NEW
        </button>
      </div>

      {showCreate && <CreateProjectDialog onClose={() => setShowCreate(false)} />}

      <table className="data-table">
        <thead>
          <tr>
            <th>PROJECT COMPONENT</th>
            <th>IDENTIFIER</th>
            <th>ARCHITECTURE</th>
            <th style={{ width: 100 }}>STATUS</th>
            <th style={{ width: 100, textAlign: 'right' }}>VOLUME</th>
            <th style={{ width: 100 }}>ACTION</th>
          </tr>
        </thead>
        <tbody>
          {data?.items.map((p) => (
            <tr key={p._id}>
              <td>
                <strong style={{ fontSize: 15, fontWeight: 500 }}>{p.name}</strong>
                {p.description && (
                  <div style={{ fontSize: 12, color: 'var(--tg-text-dim)', marginTop: 2 }}>
                    {p.description.slice(0, 80)}
                  </div>
                )}
              </td>
              <td className="mono">{p.slug ?? '--'}</td>
              <td className="mono">{p.type ?? '--'}</td>
              <td className="mono" style={{ color: p.active ? 'var(--tg-success)' : 'var(--tg-text-dim)' }}>
                {p.active ? 'ONLINE' : 'OFFLINE'}
              </td>
              <td className="mono right">{p.ticket_count ?? 0}</td>
              <td>
                <button
                  type="button"
                  onClick={() => {
                    if (confirm(`Confirm destruction of ${p.name}? This action cannot be undone.`)) deleteMut.mutate(p._id);
                  }}
                  className="btn btn-ghost btn-sm"
                  style={{ color: 'var(--tg-danger)', borderColor: 'var(--tg-danger)', clipPath: 'polygon(0 0, 100% 0, 100% calc(100% - 6px), calc(100% - 6px) 100%, 0 100%)' }}
                >
                  PURGE
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CreateProjectDialog({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [slug, setSlug] = useState('');
  const [name, setName] = useState('');
  const [template, setTemplate] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: () =>
      api('/api/v1/projects', {
        method: 'POST',
        body: JSON.stringify({
          project_slug: slug.trim(),
          name: name.trim(),
          template_slug: template,
        }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin-projects'] });
      onClose();
    },
    onError: (e) => setError(String(e)),
  });

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()} style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
        <h2 style={{ margin: 0, fontSize: 20, fontWeight: 600 }}>PROVISION ARCHITECTURE</h2>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <label className="label">SYSTEM IDENTIFIER (SLUG)</label>
            <input
              type="text"
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
              placeholder="billing"
              className="input"
              style={{ fontFamily: 'IBM Plex Mono, monospace' }}
            />
          </div>

          <div>
            <label className="label">DISPLAY NAME</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Billing & Payments"
              className="input"
            />
          </div>

          <div>
            <label className="label">BASE TOPOLOGY (OPTIONAL)</label>
            <div className="tiles">
              {TEMPLATES.map((t) => {
                const active = template === t.slug;
                return (
                  <button
                    key={t.slug}
                    type="button"
                    onClick={() => setTemplate(active ? null : t.slug)}
                    className={`tile${active ? ' tile-active' : ''}`}
                    style={{ display: 'flex', alignItems: 'center', gap: 8, padding: 12 }}
                  >
                    {active ? (
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square" style={{ color: 'var(--tg-accent)' }}>
                        <polyline points="20 6 9 17 4 12"></polyline>
                      </svg>
                    ) : (
                      <span style={{ width: 14 }} />
                    )}
                    <span style={{ fontSize: 13 }}>{t.label}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {error && (
          <div style={{ padding: 12, border: '1px solid var(--tg-danger)', background: 'var(--tg-danger-soft)', color: 'var(--tg-text)', fontSize: 13, fontFamily: 'IBM Plex Mono, monospace' }}>
            ERROR: {error}
          </div>
        )}

        <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
          <button
            type="button"
            onClick={() => create.mutate()}
            disabled={!slug.trim() || !name.trim() || create.isPending}
            className="btn btn-primary"
            style={{ flex: 1, padding: '14px', fontSize: 14 }}
          >
            {create.isPending ? 'PROVISIONING...' : 'PROVISION'}
          </button>
          <button type="button" onClick={onClose} className="btn btn-ghost" style={{ padding: '14px 20px' }}>
            ABORT
          </button>
        </div>
      </div>
    </div>
  );
}
