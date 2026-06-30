import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  archiveProject,
  deleteProject,
  getProject,
  restoreProject,
  updateProject,
  type Project,
} from '@/lib/api';
import { ConfirmDialog } from '@/components/ConfirmDialog';

export function ProjectDetail() {
  const { id = '' } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const navigate = useNavigate();

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['admin-project', id],
    queryFn: () => getProject(id),
    enabled: !!id,
  });

  const [form, setForm] = useState<Partial<Project>>({});
  const [confirmPurge, setConfirmPurge] = useState(false);

  // Seed the editable form once the project loads.
  useEffect(() => {
    if (data) {
      setForm({
        name: data.name,
        description: data.description ?? '',
        type: data.type ?? 'support',
        has_rating: data.has_rating ?? false,
        has_text: data.has_text ?? true,
      });
    }
  }, [data]);

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['admin-project', id] });
    qc.invalidateQueries({ queryKey: ['admin-projects'] });
  };

  const save = useMutation({
    mutationFn: () => updateProject(id, form),
    onSuccess: invalidate,
  });
  const archive = useMutation({
    mutationFn: () => (data?.active ? archiveProject(id) : restoreProject(id)),
    onSuccess: invalidate,
  });
  const purge = useMutation({
    mutationFn: () => deleteProject(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin-projects'] });
      navigate('/admin/projects', { replace: true });
    },
    onSettled: () => setConfirmPurge(false),
  });

  if (isLoading) return <div className="skeleton skeleton-block" style={{ height: 200 }} />;
  if (isError || !data) {
    const forbidden = String(error).includes('403');
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <BackLink />
        <div style={{ padding: 12, border: '1px solid var(--tg-danger)', background: 'var(--tg-danger-soft)', fontSize: 13, fontFamily: 'IBM Plex Mono, monospace' }}>
          ERROR: {forbidden ? 'INSUFFICIENT PERMISSIONS' : String(error || 'not found')}
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24, maxWidth: 720 }}>
      <BackLink />
      <div className="heading-row" style={{ marginBottom: 0 }}>
        <h1 className="heading">{data.name}</h1>
        <span className="mono" style={{ color: data.active ? 'var(--tg-success)' : 'var(--tg-text-dim)', fontSize: 12 }}>
          {data.active ? 'ONLINE' : 'ARCHIVED'} · {data.ticket_count ?? 0} TICKETS
        </span>
      </div>

      {/* Editable fields */}
      <section className="stack" style={{ gap: 16 }}>
        <div className="stack" style={{ gap: 6 }}>
          <label className="label">DISPLAY NAME</label>
          <input className="input" value={form.name ?? ''} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </div>
        <div className="stack" style={{ gap: 6 }}>
          <label className="label">DESCRIPTION</label>
          <textarea className="textarea" rows={3} value={form.description ?? ''} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        </div>
        <div className="stack" style={{ gap: 6 }}>
          <label className="label">TYPE</label>
          <select className="select" value={form.type ?? 'support'} onChange={(e) => setForm({ ...form, type: e.target.value })}>
            <option value="support">support</option>
            <option value="feedback">feedback</option>
            <option value="contact">contact</option>
          </select>
        </div>
        <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 13, fontFamily: 'IBM Plex Mono, monospace' }}>
            <input type="checkbox" checked={!!form.has_text} onChange={(e) => setForm({ ...form, has_text: e.target.checked })} style={{ accentColor: 'var(--tg-accent)', width: 16, height: 16 }} />
            ACCEPTS TEXT
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 13, fontFamily: 'IBM Plex Mono, monospace' }}>
            <input type="checkbox" checked={!!form.has_rating} onChange={(e) => setForm({ ...form, has_rating: e.target.checked })} style={{ accentColor: 'var(--tg-accent)', width: 16, height: 16 }} />
            ACCEPTS RATING
          </label>
        </div>
        <div>
          <button type="button" onClick={() => save.mutate()} disabled={save.isPending} className="btn btn-primary" style={{ padding: '12px 24px' }}>
            {save.isPending && <span className="spinner" />}
            {save.isPending ? 'SAVING...' : save.isSuccess ? 'SAVED ✓' : 'SAVE CHANGES'}
          </button>
        </div>
      </section>

      {/* Danger zone */}
      <section style={{ border: '1px solid var(--tg-danger)', background: 'var(--tg-danger-soft)', padding: 20, marginTop: 8, display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: 12, color: 'var(--tg-danger)', textTransform: 'uppercase', fontWeight: 600 }}>
          ⚠ Danger zone
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <div style={{ fontSize: 13, color: 'var(--tg-text-dim)' }}>
            {data.active ? 'Archive hides this project from intake. Reversible.' : 'Restore re-enables this project for intake.'}
          </div>
          <button type="button" onClick={() => archive.mutate()} disabled={archive.isPending} className="btn btn-ghost btn-sm">
            {archive.isPending ? '...' : data.active ? 'ARCHIVE' : 'RESTORE'}
          </button>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap', borderTop: '1px solid var(--tg-danger)', paddingTop: 16 }}>
          <div style={{ fontSize: 13, color: 'var(--tg-text-dim)' }}>
            Permanently delete this project. {(data.ticket_count ?? 0) > 0 && (
              <strong style={{ color: 'var(--tg-text)' }}>{data.ticket_count} ticket(s) will be kept but unlinked.</strong>
            )} This cannot be undone.
          </div>
          <button type="button" onClick={() => setConfirmPurge(true)} className="btn btn-danger btn-sm">
            PURGE
          </button>
        </div>
      </section>

      <ConfirmDialog
        open={confirmPurge}
        danger
        title="Purge project?"
        body={
          <>
            This permanently deletes <strong>{data.name}</strong> and cannot be undone.
            {(data.ticket_count ?? 0) > 0 && ` ${data.ticket_count} ticket(s) will be kept but unlinked.`}
          </>
        }
        requireText={data.name}
        confirmLabel="PURGE FOREVER"
        busy={purge.isPending}
        onConfirm={() => purge.mutate()}
        onCancel={() => setConfirmPurge(false)}
      />
    </div>
  );
}

function BackLink() {
  return (
    <Link to="/admin/projects" style={{ fontSize: 13, fontFamily: 'IBM Plex Mono, monospace', color: 'var(--tg-text-dim)', textTransform: 'uppercase', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square">
        <line x1="19" y1="12" x2="5" y2="12"></line>
        <polyline points="12 19 5 12 12 5"></polyline>
      </svg>
      ALL PROJECTS
    </Link>
  );
}
