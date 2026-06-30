import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  createKb,
  createMacro,
  deleteKb,
  deleteMacro,
  listKb,
  listMacros,
  updateKb,
  updateMacro,
  type KbArticle,
  type Macro,
} from '@/lib/api';
import { ConfirmDialog } from '@/components/ConfirmDialog';

export function Content() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 40, maxWidth: 880 }}>
      <div className="heading-row" style={{ marginBottom: 0 }}>
        <h1 className="heading">CONTENT</h1>
      </div>
      <MacrosSection />
      <KbSection />
    </div>
  );
}

function MacrosSection() {
  const qc = useQueryClient();
  const { data, isError, error } = useQuery({ queryKey: ['macros'], queryFn: listMacros });
  const [name, setName] = useState('');
  const [body, setBody] = useState('');
  const [editId, setEditId] = useState<string | null>(null);
  const [editBody, setEditBody] = useState('');
  const [pendingDelete, setPendingDelete] = useState<Macro | null>(null);
  const inv = () => qc.invalidateQueries({ queryKey: ['macros'] });

  const create = useMutation({ mutationFn: () => createMacro(name.trim(), body), onSuccess: () => { setName(''); setBody(''); inv(); } });
  const save = useMutation({ mutationFn: () => updateMacro(editId!, editBody), onSuccess: () => { setEditId(null); inv(); } });
  const del = useMutation({ mutationFn: (id: string) => deleteMacro(id), onSuccess: inv, onSettled: () => setPendingDelete(null) });

  if (isError) return <SectionError title="MACROS" error={error} />;

  return (
    <section style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <p className="section-title">MACROS — canned reply templates</p>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-start' }}>
        <input className="input" placeholder="name (a-z0-9_-)" value={name} onChange={(e) => setName(e.target.value)} style={{ width: 180, fontFamily: 'IBM Plex Mono, monospace' }} />
        <input className="input" placeholder="reply body" value={body} onChange={(e) => setBody(e.target.value)} style={{ flex: 1, minWidth: 200 }} />
        <button type="button" className="btn btn-primary btn-sm" disabled={!name.trim() || !body.trim() || create.isPending} onClick={() => create.mutate()}>
          {create.isPending ? '...' : 'ADD'}
        </button>
      </div>
      {create.isError && <span style={{ color: 'var(--tg-danger)', fontSize: 12 }}>Failed (name taken or invalid)</span>}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {data?.items.map((m) => (
          <div key={m.id} style={{ border: '1px solid var(--tg-border)', padding: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
              <strong className="mono">{m.name}{m.team_id ? ` · ${m.team_id}` : ''}</strong>
              <div style={{ display: 'flex', gap: 6 }}>
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => { setEditId(m.id); setEditBody(m.body); }}>EDIT</button>
                <button type="button" className="btn btn-ghost btn-sm" style={{ color: 'var(--tg-danger)', borderColor: 'var(--tg-danger)' }} onClick={() => setPendingDelete(m)}>DELETE</button>
              </div>
            </div>
            {editId === m.id ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <textarea className="textarea" rows={3} value={editBody} onChange={(e) => setEditBody(e.target.value)} />
                <div style={{ display: 'flex', gap: 6 }}>
                  <button type="button" className="btn btn-primary btn-sm" disabled={save.isPending} onClick={() => save.mutate()}>SAVE</button>
                  <button type="button" className="btn btn-ghost btn-sm" onClick={() => setEditId(null)}>CANCEL</button>
                </div>
              </div>
            ) : (
              <div style={{ fontSize: 13, color: 'var(--tg-text-dim)', whiteSpace: 'pre-wrap' }}>{m.body}</div>
            )}
          </div>
        ))}
        {data && data.items.length === 0 && <span className="mono" style={{ color: 'var(--tg-text-dim)' }}>No macros yet.</span>}
      </div>

      <ConfirmDialog open={!!pendingDelete} danger title="Delete macro?"
        body={<>Delete <strong>{pendingDelete?.name}</strong>?</>} confirmLabel="DELETE" busy={del.isPending}
        onConfirm={() => pendingDelete && del.mutate(pendingDelete.id)} onCancel={() => setPendingDelete(null)} />
    </section>
  );
}

function KbSection() {
  const qc = useQueryClient();
  const { data, isError, error } = useQuery({ queryKey: ['kb'], queryFn: listKb });
  const [slug, setSlug] = useState('');
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [editSlug, setEditSlug] = useState<string | null>(null);
  const [editBody, setEditBody] = useState('');
  const [pendingDelete, setPendingDelete] = useState<KbArticle | null>(null);
  const inv = () => qc.invalidateQueries({ queryKey: ['kb'] });

  const create = useMutation({ mutationFn: () => createKb(slug.trim(), title.trim(), body), onSuccess: () => { setSlug(''); setTitle(''); setBody(''); inv(); } });
  const save = useMutation({ mutationFn: () => updateKb(editSlug!, { body: editBody }), onSuccess: () => { setEditSlug(null); inv(); } });
  const del = useMutation({ mutationFn: (s: string) => deleteKb(s), onSuccess: inv, onSettled: () => setPendingDelete(null) });

  if (isError) return <SectionError title="KNOWLEDGE BASE" error={error} />;

  return (
    <section style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <p className="section-title">KNOWLEDGE BASE — help articles</p>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-start' }}>
        <input className="input" placeholder="slug" value={slug} onChange={(e) => setSlug(e.target.value)} style={{ width: 160, fontFamily: 'IBM Plex Mono, monospace' }} />
        <input className="input" placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)} style={{ width: 220 }} />
        <input className="input" placeholder="Body" value={body} onChange={(e) => setBody(e.target.value)} style={{ flex: 1, minWidth: 200 }} />
        <button type="button" className="btn btn-primary btn-sm" disabled={!slug.trim() || !title.trim() || !body.trim() || create.isPending} onClick={() => create.mutate()}>
          {create.isPending ? '...' : 'ADD'}
        </button>
      </div>
      {create.isError && <span style={{ color: 'var(--tg-danger)', fontSize: 12 }}>Failed (slug taken or invalid)</span>}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {data?.items.map((a) => (
          <div key={a.id} style={{ border: '1px solid var(--tg-border)', padding: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
              <div><strong>{a.title}</strong> <span className="mono" style={{ color: 'var(--tg-text-dim)', fontSize: 12 }}>{a.slug} · {a.lang} · {a.views} views</span></div>
              <div style={{ display: 'flex', gap: 6 }}>
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => { setEditSlug(a.slug); setEditBody(a.body); }}>EDIT</button>
                <button type="button" className="btn btn-ghost btn-sm" style={{ color: 'var(--tg-danger)', borderColor: 'var(--tg-danger)' }} onClick={() => setPendingDelete(a)}>DELETE</button>
              </div>
            </div>
            {editSlug === a.slug ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <textarea className="textarea" rows={4} value={editBody} onChange={(e) => setEditBody(e.target.value)} />
                <div style={{ display: 'flex', gap: 6 }}>
                  <button type="button" className="btn btn-primary btn-sm" disabled={save.isPending} onClick={() => save.mutate()}>SAVE</button>
                  <button type="button" className="btn btn-ghost btn-sm" onClick={() => setEditSlug(null)}>CANCEL</button>
                </div>
              </div>
            ) : (
              <div style={{ fontSize: 13, color: 'var(--tg-text-dim)', whiteSpace: 'pre-wrap' }}>{a.body.slice(0, 200)}{a.body.length > 200 ? '…' : ''}</div>
            )}
          </div>
        ))}
        {data && data.items.length === 0 && <span className="mono" style={{ color: 'var(--tg-text-dim)' }}>No articles yet.</span>}
      </div>

      <ConfirmDialog open={!!pendingDelete} danger title="Delete article?"
        body={<>Delete <strong>{pendingDelete?.title}</strong> (<code>{pendingDelete?.slug}</code>)?</>} confirmLabel="DELETE" busy={del.isPending}
        onConfirm={() => pendingDelete && del.mutate(pendingDelete.slug)} onCancel={() => setPendingDelete(null)} />
    </section>
  );
}

function SectionError({ title, error }: { title: string; error: unknown }) {
  const forbidden = String(error).includes('403') || String(error).includes('insufficient_role');
  return (
    <section style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <p className="section-title">{title}</p>
      <div style={{ padding: 12, border: '1px solid var(--tg-danger)', background: 'var(--tg-danger-soft)', fontSize: 13, fontFamily: 'IBM Plex Mono, monospace' }}>
        ERROR: {forbidden ? 'INSUFFICIENT PERMISSIONS (admin/owner only)' : String(error)}
      </div>
    </section>
  );
}
