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
    mutationFn: (id: string) =>
      api(`/api/v1/projects/${id}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-projects'] }),
  });

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <h1 style={{ margin: 0 }}>Projects</h1>
        <button
          type="button"
          onClick={() => setShowCreate(true)}
          style={{
            marginLeft: 'auto',
            padding: '8px 16px',
            background: '#2563eb',
            color: '#fff',
            border: 'none',
            borderRadius: 8,
            cursor: 'pointer',
          }}
        >
          + Create
        </button>
      </div>

      {showCreate && <CreateProjectDialog onClose={() => setShowCreate(false)} />}

      <table style={{ width: '100%', marginTop: 16, borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: '1px solid #e5e7eb', textAlign: 'left' }}>
            <Th>Name</Th>
            <Th>Slug</Th>
            <Th>Type</Th>
            <Th>Active</Th>
            <Th>Tickets</Th>
            <Th>Actions</Th>
          </tr>
        </thead>
        <tbody>
          {data?.items.map((p) => (
            <tr key={p._id} style={{ borderBottom: '1px solid #f3f4f6' }}>
              <Td>
                <strong>{p.name}</strong>
                {p.description && (
                  <div style={{ fontSize: 12, color: '#6b7280' }}>
                    {p.description.slice(0, 80)}
                  </div>
                )}
              </Td>
              <Td>
                <code>{p.slug ?? '—'}</code>
              </Td>
              <Td>{p.type ?? '—'}</Td>
              <Td>{p.active ? '✅' : '⬜'}</Td>
              <Td>{p.ticket_count ?? 0}</Td>
              <Td>
                <button
                  type="button"
                  onClick={() => {
                    if (confirm(`Delete ${p.name}?`)) deleteMut.mutate(p._id);
                  }}
                  style={{
                    padding: '4px 10px',
                    background: 'transparent',
                    color: '#991b1b',
                    border: '1px solid #fca5a5',
                    borderRadius: 6,
                    cursor: 'pointer',
                    fontSize: 12,
                  }}
                >
                  Delete
                </button>
              </Td>
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
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.3)',
        display: 'grid',
        placeItems: 'center',
        zIndex: 100,
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: '#ffffff',
          borderRadius: 12,
          padding: 24,
          maxWidth: 480,
          width: '90%',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h2 style={{ marginTop: 0 }}>Create project</h2>
        <label style={{ fontSize: 13, opacity: 0.7 }}>Slug</label>
        <input
          type="text"
          value={slug}
          onChange={(e) => setSlug(e.target.value)}
          placeholder="billing"
          style={{ ...fieldStyle }}
        />
        <label style={{ fontSize: 13, opacity: 0.7, marginTop: 12, display: 'block' }}>
          Name
        </label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Billing & Payments"
          style={{ ...fieldStyle }}
        />
        <label style={{ fontSize: 13, opacity: 0.7, marginTop: 12, display: 'block' }}>
          Template (optional)
        </label>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 6 }}>
          {TEMPLATES.map((t) => {
            const active = template === t.slug;
            return (
              <button
                key={t.slug}
                type="button"
                onClick={() => setTemplate(active ? null : t.slug)}
                style={{
                  padding: '8px 10px',
                  border: active ? '2px solid #2563eb' : '1px solid #e5e7eb',
                  background: active ? '#eff6ff' : 'transparent',
                  borderRadius: 8,
                  cursor: 'pointer',
                  textAlign: 'left',
                  fontSize: 13,
                }}
              >
                {active ? '✅ ' : '· '}
                {t.label}
              </button>
            );
          })}
        </div>
        {error && <p style={{ color: '#991b1b', fontSize: 13 }}>{error}</p>}
        <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
          <button
            type="button"
            onClick={() => create.mutate()}
            disabled={!slug.trim() || !name.trim() || create.isPending}
            style={{
              flex: 1,
              padding: '10px 16px',
              background: '#2563eb',
              color: '#fff',
              border: 'none',
              borderRadius: 8,
              cursor: 'pointer',
            }}
          >
            {create.isPending ? 'Creating…' : 'Create'}
          </button>
          <button
            type="button"
            onClick={onClose}
            style={{
              padding: '10px 16px',
              background: 'transparent',
              color: '#374151',
              border: '1px solid #e5e7eb',
              borderRadius: 8,
              cursor: 'pointer',
            }}
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

const fieldStyle: React.CSSProperties = {
  width: '100%',
  padding: 8,
  border: '1px solid #e5e7eb',
  borderRadius: 8,
  fontSize: 14,
  marginTop: 4,
};

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th style={{ padding: '8px 10px', fontSize: 12, color: '#6b7280', fontWeight: 500 }}>
      {children}
    </th>
  );
}

function Td({ children }: { children: React.ReactNode }) {
  return <td style={{ padding: '10px', fontSize: 14 }}>{children}</td>;
}
