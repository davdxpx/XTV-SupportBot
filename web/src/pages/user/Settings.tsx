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
  { code: 'en', label: '🇬🇧 English' },
  { code: 'de', label: '🇩🇪 Deutsch' },
  { code: 'es', label: '🇪🇸 Español' },
  { code: 'ru', label: '🇷🇺 Русский' },
  { code: 'hi', label: '🇮🇳 हिन्दी' },
  { code: 'bn', label: '🇧🇩 বাংলা' },
];

export function UserSettings() {
  const qc = useQueryClient();
  const { data } = useQuery({
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

  if (!local) return <p className="muted">Loading…</p>;

  const patch = (p: Partial<UserSettings>) => {
    setLocal({ ...local, ...p });
    save.mutate(p);
  };

  return (
    <div className="stack stack-lg">
      <h2 className="heading">⚙️ Settings</h2>

      <section>
        <p className="section-title">🌐 Language</p>
        <div className="tiles">
          {LANGUAGES.map((lang) => {
            const active = lang.code === local.language;
            return (
              <button
                key={lang.code}
                type="button"
                onClick={() => patch({ language: lang.code })}
                className={`tile${active ? ' tile-active' : ''}`}
              >
                {active ? '✅ ' : '· '}
                {lang.label}
              </button>
            );
          })}
        </div>
      </section>

      <section>
        <p className="section-title">🔔 Notifications</p>
        <div className="stack" style={{ gap: 6 }}>
          <Toggle
            label="Notify me on agent replies"
            value={local.notify_on_reply}
            onChange={(v) => patch({ notify_on_reply: v })}
          />
          <Toggle
            label="Ask for satisfaction after close"
            value={local.notify_csat}
            onChange={(v) => patch({ notify_csat: v })}
          />
          <Toggle
            label="Announcements from the team"
            value={local.notify_announcements}
            onChange={(v) => patch({ notify_announcements: v })}
          />
        </div>
      </section>

      <section>
        <p className="section-title">🖥 UI preference</p>
        <div className="stack" style={{ gap: 6 }}>
          {(
            [
              { value: null, label: 'Use server default' },
              { value: 'chat', label: 'Always use chat buttons' },
              { value: 'webapp', label: 'Always use the Web App' },
              { value: 'hybrid', label: 'Show both' },
            ] as const
          ).map((opt) => {
            const active = local.ui_pref === opt.value;
            return (
              <button
                key={String(opt.value)}
                type="button"
                onClick={() => patch({ ui_pref: opt.value })}
                className={`tile${active ? ' tile-active' : ''}`}
              >
                {active ? '✅ ' : '· '}
                {opt.label}
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
      className="tile row"
    >
      <span style={{ fontSize: 18 }}>{value ? '✅' : '⬜'}</span>
      <span>{label}</span>
    </button>
  );
}
