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

  const { data } = useQuery({
    queryKey: ['admin-projects'],
    queryFn: () => api<ProjectsResponse>('/api/v1/projects'),
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => api(`/api/v1/projects/${id}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-projects'] }),
  });

  return (
    <div className="stack stack-lg">
      <div className="heading-row">
        <h1 className="heading">Projects</h1>
        <button type="button" onClick={() => setShowCreate(true)} className="btn btn-primary">
          + Create
        </button>
      </div>

      {showCreate && <CreateProjectDialog onClose={() => setShowCreate(false)} />}

      <table className="data-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Slug</th>
            <th>Type</th>
            <th>Active</th>
            <th>Tickets</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {data?.items.map((p) => (
            <tr key={p._id}>
              <td>
                <strong>{p.name}</strong>
                {p.description && (
                  <div className="muted" style={{ fontSize: 12 }}>
                    {p.description.slice(0, 80)}
                  </div>
                )}
              </td>
              <td><code>{p.slug ?? '—'}</code></td>
              <td>{p.type ?? '—'}</td>
              <td>{p.active ? '✅' : '⬜'}</td>
              <td>{p.ticket_count ?? 0}</td>
              <td>
                <button
                  type="button"
                  onClick={() => {
                    if (confirm(`Delete ${p.name}?`)) deleteMut.mutate(p._id);
                  }}
                  className="btn btn-danger btn-sm"
                >
                  Delete
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
      <div className="modal stack" onClick={(e) => e.stopPropagation()}>
        <h2 style={{ margin: 0 }}>Create project</h2>

        <div>
          <label className="label">Slug</label>
          <input
            type="text"
            value={slug}
            onChange={(e) => setSlug(e.target.value)}
            placeholder="billing"
            className="input"
          />
        </div>

        <div>
          <label className="label">Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Billing & Payments"
            className="input"
          />
        </div>

        <div>
          <label className="label">Template (optional)</label>
          <div className="tiles">
            {TEMPLATES.map((t) => {
              const active = template === t.slug;
              return (
                <button
                  key={t.slug}
                  type="button"
                  onClick={() => setTemplate(active ? null : t.slug)}
                  className={`tile${active ? ' tile-active' : ''}`}
                >
                  {active ? '✅ ' : '· '}
                  {t.label}
                </button>
              );
            })}
          </div>
        </div>

        {error && <div className="pill pill-danger" style={{ padding: 10 }}>{error}</div>}

        <div className="row">
          <button
            type="button"
            onClick={() => create.mutate()}
            disabled={!slug.trim() || !name.trim() || create.isPending}
            className="btn btn-primary"
            style={{ flex: 1 }}
          >
            {create.isPending ? 'Creating…' : 'Create'}
          </button>
          <button type="button" onClick={onClose} className="btn btn-ghost">
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
