import { useState, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';

interface UserSettings {
  language: string;
  ui_pref: string | null;
  notify_on_reply: boolean;
  notify_csat: boolean;
  notify_announcements: boolean;
}

interface Language {
  code: string;
  name: string;
  flag: string;
}

export function UserSettings() {
  const qc = useQueryClient();
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['me-settings'],
    queryFn: () => api<UserSettings>('/api/v1/me/settings'),
  });
  const languages = useQuery({
    queryKey: ['languages'],
    queryFn: () => api<{ items: Language[] }>('/api/v1/me/languages'),
    staleTime: 5 * 60_000,
  });
  const [local, setLocal] = useState<UserSettings | null>(null);
  // Brief lockout after a change: gives clear "saving → saved" feedback and
  // discourages rapid-fire toggling.
  const [cooling, setCooling] = useState(false);

  useEffect(() => {
    if (data && !local) setLocal(data);
  }, [data, local]);

  const save = useMutation({
    mutationFn: (patch: Partial<UserSettings>) =>
      api('/api/v1/me/settings', {
        method: 'PATCH',
        body: JSON.stringify(patch),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['me-settings'] });
    },
  });

  if (isLoading) return <p className="muted">Loading…</p>;
  if (isError) return <div className="pill pill-danger">Error: {String(error)}</div>;
  if (!local) return null;

  const busy = save.isPending || cooling;

  const patch = (p: Partial<UserSettings>) => {
    if (busy) return;
    setLocal({ ...local, ...p });
    setCooling(true);
    save.mutate(p, { onSettled: () => setTimeout(() => setCooling(false), 1200) });
  };

  const status = save.isPending
    ? { text: 'SAVING…', spinner: true, color: 'var(--tg-text-dim)' }
    : save.isError
      ? { text: 'SAVE FAILED', spinner: false, color: 'var(--tg-danger)' }
      : cooling
        ? { text: '✓ SAVED', spinner: false, color: 'var(--tg-success)' }
        : null;

  const langItems: Language[] = languages.data?.items ?? [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 32, opacity: busy ? 0.85 : 1 }}>
      <header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h2 style={{ margin: 0, fontSize: 24, fontWeight: 600, letterSpacing: '-0.02em' }}>Configuration</h2>
        {status && (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 11, fontFamily: 'IBM Plex Mono, monospace', color: status.color }}>
            {status.spinner && <span className="spinner" />}
            {status.text}
          </span>
        )}
      </header>

      <section>
        <p className="section-title">Language</p>
        <div className="tiles">
          {langItems.map((lang) => {
            const active = lang.code === local.language;
            return (
              <button
                key={lang.code}
                type="button"
                disabled={busy}
                onClick={() => patch({ language: lang.code })}
                className={`tile${active ? ' tile-active' : ''}`}
                style={{ display: 'flex', alignItems: 'center', gap: 8 }}
              >
                {active ? (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square" style={{ color: 'var(--tg-accent)' }}>
                    <polyline points="20 6 9 17 4 12"></polyline>
                  </svg>
                ) : (
                  <span style={{ width: 16 }} />
                )}
                <span>{lang.flag} {lang.name}</span>
              </button>
            );
          })}
          {langItems.length === 0 && <span className="muted">Loading languages…</span>}
        </div>
      </section>

      <section>
        <p className="section-title">Notifications</p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <Toggle label="Agent replies on my tickets" value={local.notify_on_reply} disabled={busy} onChange={(v) => patch({ notify_on_reply: v })} />
          <Toggle label="Satisfaction prompts on resolution" value={local.notify_csat} disabled={busy} onChange={(v) => patch({ notify_csat: v })} />
          <Toggle label="System announcements" value={local.notify_announcements} disabled={busy} onChange={(v) => patch({ notify_announcements: v })} />
        </div>
      </section>

      <section>
        <p className="section-title">Interface Preference</p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {(
            [
              { value: null, label: 'Server Default' },
              { value: 'chat', label: 'Inline Chat Buttons' },
              { value: 'webapp', label: 'Launch Web App' },
              { value: 'hybrid', label: 'Hybrid Mode' },
            ] as const
          ).map((opt) => {
            const active = local.ui_pref === opt.value;
            return (
              <button
                key={String(opt.value)}
                type="button"
                disabled={busy}
                onClick={() => patch({ ui_pref: opt.value })}
                className={`tile${active ? ' tile-active' : ''}`}
                style={{ display: 'flex', alignItems: 'center', gap: 8 }}
              >
                {active ? (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="square" style={{ color: 'var(--tg-accent)' }}>
                    <polyline points="20 6 9 17 4 12"></polyline>
                  </svg>
                ) : (
                  <span style={{ width: 16 }} />
                )}
                <span>{opt.label}</span>
              </button>
            );
          })}
        </div>
      </section>
    </div>
  );
}

function Toggle({
  label,
  value,
  onChange,
  disabled = false,
}: {
  label: string;
  value: boolean;
  onChange: (next: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={() => onChange(!value)}
      className={`tile ${value ? 'tile-active' : ''}`}
      style={{ display: 'flex', alignItems: 'center', gap: 12 }}
    >
      <div style={{
        width: 18, height: 18, border: '2px solid',
        borderColor: value ? 'var(--tg-accent)' : 'var(--tg-border)',
        backgroundColor: value ? 'var(--tg-accent)' : 'transparent',
        display: 'flex', alignItems: 'center', justifyContent: 'center'
      }}>
        {value && (
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="var(--tg-accent-text)" strokeWidth="3" strokeLinecap="square">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
        )}
      </div>
      <span style={{ flex: 1, textAlign: 'left', fontWeight: value ? 500 : 400 }}>{label}</span>
    </button>
  );
}
