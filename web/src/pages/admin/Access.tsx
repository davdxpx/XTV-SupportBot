import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  addTeamMember,
  createTeam,
  deleteTeam,
  grantRole,
  listRoles,
  listTeams,
  removeTeamMember,
  revokeRole,
  type RoleAssignment,
  type TeamItem,
} from '@/lib/api';
import { ConfirmDialog } from '@/components/ConfirmDialog';

export function Access() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 40, maxWidth: 880 }}>
      <div className="heading-row" style={{ marginBottom: 0 }}>
        <h1 className="heading">ACCESS CONTROL</h1>
      </div>
      <RolesSection />
      <TeamsSection />
    </div>
  );
}

function RolesSection() {
  const qc = useQueryClient();
  const { data, isError, error } = useQuery({ queryKey: ['rbac-roles'], queryFn: listRoles });
  const [uid, setUid] = useState('');
  const [role, setRole] = useState('agent');
  const [pendingRevoke, setPendingRevoke] = useState<RoleAssignment | null>(null);
  const inv = () => qc.invalidateQueries({ queryKey: ['rbac-roles'] });

  const grant = useMutation({
    mutationFn: () => grantRole(Number(uid), role),
    onSuccess: () => { setUid(''); inv(); },
  });
  const revoke = useMutation({
    mutationFn: (user_id: number) => revokeRole(user_id),
    onSuccess: inv,
    onSettled: () => setPendingRevoke(null),
  });

  if (isError) {
    const forbidden = String(error).includes('403') || String(error).includes('insufficient_role');
    return <SectionError title="ROLES" forbidden={forbidden} error={error} />;
  }

  const roleOptions = data?.roles ?? ['user', 'viewer', 'agent', 'supervisor', 'admin', 'owner'];

  return (
    <section style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <p className="section-title">ROLES — grant a Telegram user a role (governs bot + console access)</p>

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
        <input className="input" placeholder="Telegram user id" value={uid} inputMode="numeric"
          onChange={(e) => setUid(e.target.value.replace(/[^0-9]/g, ''))} style={{ width: 180 }} />
        <select className="select" value={role} onChange={(e) => setRole(e.target.value)} style={{ width: 160 }}>
          {roleOptions.map((r) => <option key={r} value={r}>{r.toUpperCase()}</option>)}
        </select>
        <button type="button" className="btn btn-primary btn-sm" disabled={!uid || grant.isPending} onClick={() => grant.mutate()}>
          {grant.isPending ? '...' : 'GRANT'}
        </button>
        {grant.isError && <span style={{ color: 'var(--tg-danger)', fontSize: 12 }}>{String(grant.error).includes('403') ? 'Not allowed (above your rank)' : 'Failed'}</span>}
      </div>

      <div className="table-scroll">
        <table className="data-table">
          <thead><tr><th>USER ID</th><th>ROLE</th><th>TEAMS</th><th></th></tr></thead>
          <tbody>
            {data?.items.map((a) => (
              <tr key={a.user_id}>
                <td className="mono">{a.user_id}</td>
                <td className="mono" style={{ textTransform: 'uppercase' }}>{a.role}</td>
                <td className="mono" style={{ color: 'var(--tg-text-dim)' }}>{a.team_ids.join(', ') || '—'}</td>
                <td style={{ textAlign: 'right' }}>
                  <button type="button" className="btn btn-ghost btn-sm" style={{ color: 'var(--tg-danger)', borderColor: 'var(--tg-danger)' }} onClick={() => setPendingRevoke(a)}>
                    REVOKE
                  </button>
                </td>
              </tr>
            ))}
            {data && data.items.length === 0 && (
              <tr><td colSpan={4} className="mono" style={{ color: 'var(--tg-text-dim)' }}>No explicit role assignments.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <ConfirmDialog
        open={!!pendingRevoke}
        danger
        title="Revoke role?"
        body={<>Remove the role from user <strong>{pendingRevoke?.user_id}</strong>? They drop back to the default (USER).</>}
        confirmLabel="REVOKE"
        busy={revoke.isPending}
        onConfirm={() => pendingRevoke && revoke.mutate(pendingRevoke.user_id)}
        onCancel={() => setPendingRevoke(null)}
      />
    </section>
  );
}

function TeamsSection() {
  const qc = useQueryClient();
  const { data, isError, error } = useQuery({ queryKey: ['rbac-teams'], queryFn: listTeams });
  const [tid, setTid] = useState('');
  const [name, setName] = useState('');
  const [pendingDelete, setPendingDelete] = useState<TeamItem | null>(null);
  const inv = () => qc.invalidateQueries({ queryKey: ['rbac-teams'] });

  const create = useMutation({
    mutationFn: () => createTeam(tid.trim().toLowerCase(), name.trim()),
    onSuccess: () => { setTid(''); setName(''); inv(); },
  });
  const del = useMutation({
    mutationFn: (id: string) => deleteTeam(id),
    onSuccess: inv,
    onSettled: () => setPendingDelete(null),
  });

  if (isError) {
    const forbidden = String(error).includes('403') || String(error).includes('insufficient_role');
    return <SectionError title="TEAMS" forbidden={forbidden} error={error} />;
  }

  return (
    <section style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <p className="section-title">TEAMS — group agents for routing</p>

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
        <input className="input" placeholder="slug (a-z0-9-_)" value={tid} onChange={(e) => setTid(e.target.value)} style={{ width: 180, fontFamily: 'IBM Plex Mono, monospace' }} />
        <input className="input" placeholder="Display name" value={name} onChange={(e) => setName(e.target.value)} style={{ width: 220 }} />
        <button type="button" className="btn btn-primary btn-sm" disabled={!tid.trim() || !name.trim() || create.isPending} onClick={() => create.mutate()}>
          {create.isPending ? '...' : 'CREATE TEAM'}
        </button>
        {create.isError && <span style={{ color: 'var(--tg-danger)', fontSize: 12 }}>Failed (slug taken or invalid)</span>}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {data?.items.map((t) => (
          <TeamRow key={t.id} team={t} onChanged={inv} onDelete={() => setPendingDelete(t)} />
        ))}
        {data && data.items.length === 0 && <span className="mono" style={{ color: 'var(--tg-text-dim)' }}>No teams yet.</span>}
      </div>

      <ConfirmDialog
        open={!!pendingDelete}
        danger
        title="Delete team?"
        body={<>Permanently delete team <strong>{pendingDelete?.name}</strong> (<code>{pendingDelete?.id}</code>)?</>}
        confirmLabel="DELETE"
        busy={del.isPending}
        onConfirm={() => pendingDelete && del.mutate(pendingDelete.id)}
        onCancel={() => setPendingDelete(null)}
      />
    </section>
  );
}

function TeamRow({ team, onChanged, onDelete }: { team: TeamItem; onChanged: () => void; onDelete: () => void }) {
  const [uid, setUid] = useState('');
  const add = useMutation({ mutationFn: () => addTeamMember(team.id, Number(uid)), onSuccess: () => { setUid(''); onChanged(); } });
  const rm = useMutation({ mutationFn: (m: number) => removeTeamMember(team.id, m), onSuccess: onChanged });

  return (
    <div style={{ border: '1px solid var(--tg-border)', padding: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
        <div>
          <strong>{team.name}</strong>{' '}
          <span className="mono" style={{ color: 'var(--tg-text-dim)', fontSize: 12 }}>{team.id} · {team.timezone}</span>
        </div>
        <button type="button" className="btn btn-ghost btn-sm" style={{ color: 'var(--tg-danger)', borderColor: 'var(--tg-danger)' }} onClick={onDelete}>DELETE</button>
      </div>
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
        {team.member_ids.map((m) => (
          <span key={m} className="mono" style={{ fontSize: 12, padding: '2px 6px', background: 'var(--tg-surface-hi)', border: '1px solid var(--tg-border)', display: 'inline-flex', gap: 6 }}>
            {m}
            <button type="button" onClick={() => rm.mutate(m)} style={{ background: 'none', border: 'none', color: 'var(--tg-danger)', cursor: 'pointer', padding: 0 }}>✕</button>
          </span>
        ))}
        {team.member_ids.length === 0 && <span className="mono" style={{ fontSize: 12, color: 'var(--tg-text-dim)' }}>no members</span>}
        <input className="input" placeholder="add user id" value={uid} inputMode="numeric"
          onChange={(e) => setUid(e.target.value.replace(/[^0-9]/g, ''))} style={{ width: 120, padding: '4px 8px', fontFamily: 'IBM Plex Mono, monospace' }} />
        <button type="button" className="btn btn-ghost btn-sm" disabled={!uid || add.isPending} onClick={() => add.mutate()}>+ ADD</button>
      </div>
    </div>
  );
}

function SectionError({ title, forbidden, error }: { title: string; forbidden: boolean; error: unknown }) {
  return (
    <section style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <p className="section-title">{title}</p>
      <div style={{ padding: 12, border: '1px solid var(--tg-danger)', background: 'var(--tg-danger-soft)', fontSize: 13, fontFamily: 'IBM Plex Mono, monospace' }}>
        ERROR: {forbidden ? 'INSUFFICIENT PERMISSIONS (admin/owner only)' : String(error)}
      </div>
    </section>
  );
}
