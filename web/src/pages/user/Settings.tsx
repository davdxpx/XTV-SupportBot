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
