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

const LANGUAGES: { code: string; label: string }[] = [
  { code: 'bn', label: '🇧🇩 বাংলা' },
  { code: 'en', label: '🇬🇧 English' },
  { code: 'es', label: '🇪🇸 Español' },
  { code: 'gu', label: '🇮🇳 ગુજરાતી' },
  { code: 'hi', label: '🇮🇳 हिन्दी' },
  { code: 'mr', label: '🇮🇳 मराठी' },
  { code: 'pa', label: '🇮🇳 ਪੰਜਾਬੀ' },
  { code: 'ru', label: '🇷🇺 Русский' },
  { code: 'ta', label: '🇮🇳 தமிழ்' },
  { code: 'te', label: '🇮🇳 తెలుగు' },
  { code: 'ur', label: '🇵🇰 اردو' },
];

export function UserSettings() {
  const qc = useQueryClient();
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['me-settings'],
    queryFn: () => api<UserSettings>('/api/v1/me/settings'),
  });
  const [local, setLocal] = useState<UserSettings | null>(null);

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

  const patch = (p: Partial<UserSettings>) => {
    setLocal({ ...local, ...p });
    save.mutate(p);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 32 }}>
      <header>
        <h2 style={{ margin: 0, fontSize: 24, fontWeight: 600, letterSpacing: '-0.02em' }}>Configuration</h2>
      </header>

      <section>
        <p className="section-title">Language</p>
        <div className="tiles">
          {LANGUAGES.map((lang) => {
            const active = lang.code === local.language;
            return (
              <button
                key={lang.code}
                type="button"
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
                <span>{lang.label.replace(/^[^\s]+\s/, '')}</span> {/* Strip emoji flag */}
              </button>
            );
          })}
        </div>
      </section>

      <section>
        <p className="section-title">Notifications</p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <Toggle
            label="Agent replies on my tickets"
            value={local.notify_on_reply}
            onChange={(v) => patch({ notify_on_reply: v })}
          />
          <Toggle
            label="Satisfaction prompts on resolution"
            value={local.notify_csat}
            onChange={(v) => patch({ notify_csat: v })}
          />
          <Toggle
            label="System announcements"
            value={local.notify_announcements}
            onChange={(v) => patch({ notify_announcements: v })}
          />
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
}: {
  label: string;
  value: boolean;
  onChange: (next: boolean) => void;
}) {
  return (
    <button
      type="button"
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
