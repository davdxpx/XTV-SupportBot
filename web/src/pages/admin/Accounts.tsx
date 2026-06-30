import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { disableAccount, enableAccount, listAccounts } from '@/lib/api';

function fmt(ts?: string | null): string {
  if (!ts) return '—';
  try {
    return new Date(ts).toLocaleString();
  } catch {
    return ts;
  }
}

export function Accounts() {
  const qc = useQueryClient();

  const { data, isError, error } = useQuery({
    queryKey: ['admin-accounts'],
    queryFn: listAccounts,
  });

  const toggle = useMutation({
    mutationFn: ({ id, disabled }: { id: string; disabled: boolean }) =>
      disabled ? enableAccount(id) : disableAccount(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-accounts'] }),
  });

  if (isError) {
    const forbidden = String(error).includes('403') || String(error).includes('insufficient_role');
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
        <h1 className="heading">ADMIN ACCOUNTS</h1>
        <div style={{ padding: 12, border: '1px solid var(--tg-danger)', background: 'var(--tg-danger-soft)', color: 'var(--tg-text)', fontSize: 13, fontFamily: 'IBM Plex Mono, monospace' }}>
          ERROR: {forbidden ? 'INSUFFICIENT PERMISSIONS (admin/owner only)' : String(error)}
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div className="heading-row" style={{ marginBottom: 0, paddingBottom: 0, borderBottom: 'none' }}>
        <h1 className="heading">ADMIN ACCOUNTS</h1>
        <span className="mono" style={{ color: 'var(--tg-text-dim)', fontSize: 12 }}>
          {data?.count ?? 0} TOTAL
        </span>
      </div>

      <div className="table-scroll">
      <table className="data-table">
        <thead>
          <tr>
            <th>USERNAME</th>
            <th>NAME</th>
            <th>TG ID</th>
            <th>ROLE</th>
            <th>LAST LOGIN</th>
            <th>STATUS</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {data?.items.map((a) => {
            const disabled = !!a.disabled_at;
            return (
              <tr key={a.id} style={{ opacity: disabled ? 0.55 : 1 }}>
                <td><strong>{a.display_username}</strong></td>
                <td>{[a.first_name, a.last_name].filter(Boolean).join(' ')}</td>
                <td className="mono">{a.telegram_user_id}</td>
                <td className="mono" style={{ textTransform: 'uppercase' }}>{a.role ?? '—'}</td>
                <td className="mono" style={{ fontSize: 12 }}>{fmt(a.last_login_at)}</td>
                <td>
                  <span style={{
                    fontSize: 10, fontFamily: 'IBM Plex Mono, monospace', padding: '2px 6px',
                    background: disabled ? 'var(--tg-surface-hi)' : 'var(--tg-success)',
                    color: disabled ? 'var(--tg-text-dim)' : 'var(--tg-bg)',
                  }}>
                    {disabled ? 'DISABLED' : 'ACTIVE'}
                  </span>
                </td>
                <td style={{ textAlign: 'right' }}>
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    disabled={toggle.isPending}
                    onClick={() => toggle.mutate({ id: a.id, disabled })}
                    style={disabled ? undefined : { color: 'var(--tg-danger)', borderColor: 'var(--tg-danger)' }}
                  >
                    {disabled ? 'ENABLE' : 'DISABLE'}
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      </div>
    </div>
  );
}
