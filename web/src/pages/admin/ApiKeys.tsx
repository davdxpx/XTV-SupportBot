import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  createApiKey,
  listApiKeys,
  revokeApiKey,
  type ApiKeyItem,
  type NewApiKeyResult,
} from '@/lib/api';
import { ConfirmDialog } from '@/components/ConfirmDialog';

function fmt(ts?: string | null): string {
  if (!ts) return '—';
  try {
    return new Date(ts).toLocaleString();
  } catch {
    return ts;
  }
}

export function ApiKeys() {
  const qc = useQueryClient();
  const { data, isError, error } = useQuery({ queryKey: ['api-keys'], queryFn: listApiKeys });
  const [pendingRevoke, setPendingRevoke] = useState<ApiKeyItem | null>(null);
  const [created, setCreated] = useState<NewApiKeyResult | null>(null);
  const inv = () => qc.invalidateQueries({ queryKey: ['api-keys'] });

  // create form
  const [label, setLabel] = useState('');
  const [scopes, setScopes] = useState<string[]>([]);
  const [invite, setInvite] = useState(false);
  const [target, setTarget] = useState('');

  const create = useMutation({
    mutationFn: () =>
      createApiKey(
        invite
          ? { label, allow_registration: true, target_user_id: Number(target) }
          : { label, scopes },
      ),
    onSuccess: (res) => {
      setCreated(res);
      setLabel(''); setScopes([]); setInvite(false); setTarget('');
      inv();
    },
  });
  const revoke = useMutation({
    mutationFn: (id: string) => revokeApiKey(id),
    onSuccess: inv,
    onSettled: () => setPendingRevoke(null),
  });

  if (isError) {
    const forbidden = String(error).includes('403') || String(error).includes('insufficient_role');
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
        <h1 className="heading">API KEYS</h1>
        <div style={{ padding: 12, border: '1px solid var(--tg-danger)', background: 'var(--tg-danger-soft)', fontSize: 13, fontFamily: 'IBM Plex Mono, monospace' }}>
          ERROR: {forbidden ? 'INSUFFICIENT PERMISSIONS (admin/owner only)' : String(error)}
        </div>
      </div>
    );
  }

  const allScopes = data?.scopes ?? [];
  const canCreate = !!label.trim() && (invite ? !!target : scopes.length > 0) && !create.isPending;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24, maxWidth: 880 }}>
      <div className="heading-row" style={{ marginBottom: 0 }}>
        <h1 className="heading">API KEYS</h1>
      </div>

      {created && (
        <div style={{ border: '1px solid var(--tg-accent)', background: 'var(--tg-accent-soft)', padding: 16, display: 'flex', flexDirection: 'column', gap: 8 }}>
          <strong style={{ fontSize: 13 }}>
            {created.key.registration_capable ? '🎟 Invite key created' : '🔑 API key created'} — copy it now, it won't be shown again:
          </strong>
          <code style={{ wordBreak: 'break-all', fontSize: 13 }}>{created.plaintext}</code>
          {created.key.registration_capable && (
            <span style={{ fontSize: 12, color: 'var(--tg-text-dim)' }}>
              Single-use invite for Telegram id {created.key.target_user_id}. They register at the “Create your account” screen.
            </span>
          )}
          <button type="button" className="btn btn-ghost btn-sm" style={{ alignSelf: 'flex-start' }} onClick={() => setCreated(null)}>DISMISS</button>
        </div>
      )}

      {/* Create form */}
      <section style={{ display: 'flex', flexDirection: 'column', gap: 12, border: '1px solid var(--tg-border)', padding: 16 }}>
        <p className="section-title" style={{ margin: 0 }}>MINT A KEY</p>
        <input className="input" placeholder="Label (e.g. crm-sync)" value={label} onChange={(e) => setLabel(e.target.value)} style={{ maxWidth: 320 }} />
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, fontFamily: 'IBM Plex Mono, monospace', cursor: 'pointer' }}>
          <input type="checkbox" checked={invite} onChange={(e) => setInvite(e.target.checked)} style={{ accentColor: 'var(--tg-accent)', width: 16, height: 16 }} />
          REGISTRATION INVITE (single-use, creates one admin account)
        </label>

        {invite ? (
          <input className="input" placeholder="Invitee Telegram user id" value={target} inputMode="numeric"
            onChange={(e) => setTarget(e.target.value.replace(/[^0-9]/g, ''))} style={{ maxWidth: 240, fontFamily: 'IBM Plex Mono, monospace' }} />
        ) : (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {allScopes.map((s) => {
              const on = scopes.includes(s);
              return (
                <button key={s} type="button"
                  onClick={() => setScopes(on ? scopes.filter((x) => x !== s) : [...scopes, s])}
                  className={`chip${on ? ' chip-active' : ''}`}
                  style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: 12 }}>
                  {s}
                </button>
              );
            })}
          </div>
        )}

        <div>
          <button type="button" className="btn btn-primary btn-sm" disabled={!canCreate} onClick={() => create.mutate()}>
            {create.isPending ? 'MINTING...' : invite ? 'CREATE INVITE' : 'CREATE KEY'}
          </button>
          {create.isError && <span style={{ color: 'var(--tg-danger)', fontSize: 12, marginLeft: 8 }}>Failed: {String(create.error)}</span>}
        </div>
      </section>

      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr><th>LABEL</th><th>SCOPES / TYPE</th><th>LAST USED</th><th>STATUS</th><th></th></tr>
          </thead>
          <tbody>
            {data?.items.map((k) => {
              const revoked = !!k.revoked_at;
              return (
                <tr key={k.key_id} style={{ opacity: revoked ? 0.5 : 1 }}>
                  <td><strong>{k.label}</strong></td>
                  <td className="mono" style={{ fontSize: 12 }}>
                    {k.registration_capable ? `🎟 invite → ${k.target_user_id}` : (k.scopes.join(', ') || '—')}
                  </td>
                  <td className="mono" style={{ fontSize: 12 }}>{fmt(k.last_used_at)}</td>
                  <td>
                    <span style={{ fontSize: 10, fontFamily: 'IBM Plex Mono, monospace', padding: '2px 6px', background: revoked ? 'var(--tg-surface-hi)' : 'var(--tg-success)', color: revoked ? 'var(--tg-text-dim)' : 'var(--tg-bg)' }}>
                      {revoked ? 'REVOKED' : k.registration_used_at ? 'USED' : 'ACTIVE'}
                    </span>
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    {!revoked && (
                      <button type="button" className="btn btn-ghost btn-sm" style={{ color: 'var(--tg-danger)', borderColor: 'var(--tg-danger)' }} onClick={() => setPendingRevoke(k)}>
                        REVOKE
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
            {data && data.items.length === 0 && (
              <tr><td colSpan={5} className="mono" style={{ color: 'var(--tg-text-dim)' }}>No keys yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <ConfirmDialog
        open={!!pendingRevoke}
        danger
        title="Revoke key?"
        body={<>Revoke <strong>{pendingRevoke?.label}</strong>? Any client using it starts getting 401 immediately.</>}
        confirmLabel="REVOKE"
        busy={revoke.isPending}
        onConfirm={() => pendingRevoke && revoke.mutate(pendingRevoke.key_id)}
        onCancel={() => setPendingRevoke(null)}
      />
    </div>
  );
}
