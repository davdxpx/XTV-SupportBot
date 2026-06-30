import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { cancelBroadcast, createBroadcast, listBroadcasts } from '@/lib/api';
import { ConfirmDialog } from '@/components/ConfirmDialog';

function fmt(ts?: string | null): string {
  if (!ts) return '—';
  try {
    return new Date(ts).toLocaleString();
  } catch {
    return ts;
  }
}

export function Broadcasts() {
  const qc = useQueryClient();
  const { data, isError, error } = useQuery({
    queryKey: ['broadcasts'],
    queryFn: listBroadcasts,
    refetchInterval: (q) => (q.state.data?.active ? 3000 : false),
  });
  const [text, setText] = useState('');
  const [confirmSend, setConfirmSend] = useState(false);
  const inv = () => qc.invalidateQueries({ queryKey: ['broadcasts'] });

  const send = useMutation({
    mutationFn: () => createBroadcast(text.trim()),
    onSuccess: () => { setText(''); inv(); },
    onSettled: () => setConfirmSend(false),
  });
  const cancel = useMutation({ mutationFn: cancelBroadcast, onSuccess: inv });

  if (isError) {
    const forbidden = String(error).includes('403') || String(error).includes('insufficient_role');
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
        <h1 className="heading">BROADCASTS</h1>
        <div style={{ padding: 12, border: '1px solid var(--tg-danger)', background: 'var(--tg-danger-soft)', fontSize: 13, fontFamily: 'IBM Plex Mono, monospace' }}>
          ERROR: {forbidden ? 'INSUFFICIENT PERMISSIONS (admin/owner only)' : String(error)}
        </div>
      </div>
    );
  }

  const active = data?.active ?? false;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24, maxWidth: 880 }}>
      <div className="heading-row" style={{ marginBottom: 0 }}>
        <h1 className="heading">BROADCASTS</h1>
        {active && (
          <button type="button" className="btn btn-ghost btn-sm" style={{ color: 'var(--tg-danger)', borderColor: 'var(--tg-danger)' }}
            disabled={cancel.isPending} onClick={() => cancel.mutate()}>
            CANCEL RUNNING
          </button>
        )}
      </div>

      <section style={{ display: 'flex', flexDirection: 'column', gap: 12, border: '1px solid var(--tg-border)', padding: 16 }}>
        <p className="section-title" style={{ margin: 0 }}>COMPOSE — sent to every active user</p>
        <textarea className="textarea" rows={4} value={text} onChange={(e) => setText(e.target.value)}
          placeholder="Message body (HTML allowed). This reaches ALL active users." disabled={active} />
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: 11, fontFamily: 'IBM Plex Mono, monospace', color: 'var(--tg-text-dim)' }}>{text.length} / 4096</span>
          <button type="button" className="btn btn-primary btn-sm" disabled={!text.trim() || active || send.isPending} onClick={() => setConfirmSend(true)}>
            {active ? 'BROADCAST RUNNING…' : send.isPending ? 'STARTING…' : 'SEND BROADCAST'}
          </button>
        </div>
        {send.isError && <span style={{ color: 'var(--tg-danger)', fontSize: 12 }}>{String(send.error).includes('409') ? 'A broadcast is already running.' : String(send.error).includes('503') ? 'Bot not available to send.' : 'Failed.'}</span>}
      </section>

      <div className="table-scroll">
        <table className="data-table">
          <thead><tr><th>MESSAGE</th><th>STATE</th><th>SENT / TOTAL</th><th>FAILED</th><th>STARTED</th></tr></thead>
          <tbody>
            {data?.items.map((b) => (
              <tr key={b.id}>
                <td>{b.text.slice(0, 60)}{b.text.length > 60 ? '…' : ''}</td>
                <td className="mono" style={{ textTransform: 'uppercase', color: b.state === 'running' ? 'var(--tg-success)' : 'var(--tg-text-dim)' }}>{b.state}</td>
                <td className="mono">{b.sent} / {b.total}</td>
                <td className="mono">{b.failed}</td>
                <td className="mono" style={{ fontSize: 12 }}>{fmt(b.started_at)}</td>
              </tr>
            ))}
            {data && data.items.length === 0 && (
              <tr><td colSpan={5} className="mono" style={{ color: 'var(--tg-text-dim)' }}>No broadcasts yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <ConfirmDialog
        open={confirmSend}
        danger
        title="Send to all users?"
        body="This message will be delivered to every active user of the bot. This cannot be undone once started."
        requireText="SEND"
        confirmLabel="SEND BROADCAST"
        busy={send.isPending}
        onConfirm={() => send.mutate()}
        onCancel={() => setConfirmSend(false)}
      />
    </div>
  );
}
