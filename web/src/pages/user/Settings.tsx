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

  if (!local) return <p>Loading…</p>;

  const patch = (p: Partial<UserSettings>) => {
    setLocal({ ...local, ...p });
    save.mutate(p);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <h2 style={{ margin: 0 }}>⚙️ Settings</h2>

      <section>
        <h3 style={{ fontSize: 14, opacity: 0.7, marginBottom: 8 }}>
          🌐 Language
        </h3>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(2, 1fr)',
            gap: 6,
          }}
        >
          {LANGUAGES.map((lang) => {
            const active = lang.code === local.language;
            return (
              <button
                key={lang.code}
                type="button"
                onClick={() => patch({ language: lang.code })}
                style={{
                  padding: '10px 12px',
                  border: active
                    ? '2px solid #2563eb'
                    : '1px solid #e5e7eb',
                  background: active ? '#eff6ff' : 'transparent',
                  borderRadius: 10,
                  cursor: 'pointer',
                  textAlign: 'left',
                }}
              >
                {active ? '✅' : '·'} {lang.label}
              </button>
            );
          })}
        </div>
      </section>

      <section>
        <h3 style={{ fontSize: 14, opacity: 0.7, marginBottom: 8 }}>
          🔔 Notifications
        </h3>
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
      </section>

      <section>
        <h3 style={{ fontSize: 14, opacity: 0.7, marginBottom: 8 }}>
          🖥 UI preference
        </h3>
        <div style={{ display: 'grid', gap: 6 }}>
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
                style={{
                  padding: '10px 12px',
                  border: active
                    ? '2px solid #2563eb'
                    : '1px solid #e5e7eb',
                  background: active ? '#eff6ff' : 'transparent',
                  borderRadius: 10,
                  cursor: 'pointer',
                  textAlign: 'left',
                }}
              >
                {active ? '✅' : '·'} {opt.label}
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
      style={{
        width: '100%',
        padding: '12px 14px',
        border: '1px solid #e5e7eb',
        background: 'transparent',
        borderRadius: 10,
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        textAlign: 'left',
        marginBottom: 6,
      }}
    >
      <span style={{ fontSize: 18 }}>{value ? '✅' : '⬜'}</span>
      <span>{label}</span>
    </button>
  );
}
