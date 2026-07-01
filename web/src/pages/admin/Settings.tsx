import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { getSettings, patchSettings, type SettingItem } from '@/lib/api';

type Draft = Record<string, string | number>;

function groupBySection(items: SettingItem[]): [string, SettingItem[]][] {
  const map = new Map<string, SettingItem[]>();
  for (const it of items) {
    const arr = map.get(it.section) ?? [];
    arr.push(it);
    map.set(it.section, arr);
  }
  return [...map.entries()];
}

export function Settings() {
  const qc = useQueryClient();
  const { data, isLoading, isError, error } = useQuery({ queryKey: ['settings'], queryFn: getSettings });
  const [draft, setDraft] = useState<Draft>({});

  const items = data?.items ?? [];
  const sections = useMemo(() => groupBySection(items), [items]);

  const dirty = useMemo(() => {
    const out: Draft = {};
    for (const it of items) {
      if (it.key in draft && String(draft[it.key]) !== String(it.value)) out[it.key] = draft[it.key];
    }
    return out;
  }, [draft, items]);
  const dirtyCount = Object.keys(dirty).length;

  const save = useMutation({
    mutationFn: () => patchSettings(dirty),
    onSuccess: (res) => {
      qc.setQueryData(['settings'], res);
      setDraft({});
    },
  });

  const set = (key: string, value: string | number) => setDraft((d) => ({ ...d, [key]: value }));
  const valueOf = (it: SettingItem) => (it.key in draft ? draft[it.key] : it.value);

  if (isError) {
    const forbidden = String(error).includes('403') || String(error).includes('insufficient_role');
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
        <h1 className="heading">SETTINGS</h1>
        <div style={{ padding: 12, border: '1px solid var(--tg-danger)', background: 'var(--tg-danger-soft)', fontSize: 13, fontFamily: 'IBM Plex Mono, monospace' }}>
          ERROR: {forbidden ? 'INSUFFICIENT PERMISSIONS (admin/owner only)' : String(error)}
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24, maxWidth: 760 }}>
      <div className="heading-row" style={{ marginBottom: 0 }}>
        <h1 className="heading">SETTINGS</h1>
        <button
          type="button"
          className="btn btn-primary btn-sm"
          disabled={dirtyCount === 0 || save.isPending}
          onClick={() => save.mutate()}
        >
          {save.isPending ? 'SAVING…' : dirtyCount > 0 ? `SAVE ${dirtyCount} CHANGE${dirtyCount > 1 ? 'S' : ''}` : 'SAVED'}
        </button>
      </div>

      <p className="muted" style={{ margin: 0, color: 'var(--tg-text-dim)', fontSize: 13 }}>
        Operational knobs, applied live — no redeploy. Secrets and infrastructure stay in the environment.
      </p>

      {save.isError && (
        <div style={{ color: 'var(--tg-danger)', fontSize: 12 }}>Could not save: {String(save.error)}</div>
      )}
      {save.isSuccess && dirtyCount === 0 && (
        <div style={{ color: 'var(--tg-success)', fontSize: 12 }}>Saved. Changes take effect within seconds.</div>
      )}

      {isLoading && <div className="skeleton" style={{ height: 200 }} />}

      {sections.map(([section, rows]) => (
        <section key={section} style={{ display: 'flex', flexDirection: 'column', gap: 12, border: '1px solid var(--tg-border)', padding: 16 }}>
          <p className="section-title" style={{ margin: 0 }}>{section.toUpperCase()}</p>
          {rows.map((it) => (
            <div key={it.key} style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 12, alignItems: 'center' }}>
              <div style={{ minWidth: 0 }}>
                <div style={{ fontSize: 14 }}>{it.label}{it.overridden && <span style={{ color: 'var(--tg-accent)', marginLeft: 6, fontSize: 10, fontFamily: 'IBM Plex Mono, monospace' }}>● OVERRIDDEN</span>}</div>
                {it.help && <div style={{ fontSize: 11, color: 'var(--tg-text-dim)' }}>{it.help}</div>}
                <div style={{ fontSize: 10, color: 'var(--tg-text-dim)', fontFamily: 'IBM Plex Mono, monospace' }}>{it.key} · default {String(it.default)}</div>
              </div>
              {it.type === 'choice' && it.choices ? (
                <select className="input" style={{ width: 160 }} value={String(valueOf(it))} onChange={(e) => set(it.key, e.target.value)}>
                  {it.choices.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              ) : it.type === 'int' ? (
                <input
                  className="input" type="number" style={{ width: 160 }}
                  min={it.min ?? undefined} max={it.max ?? undefined}
                  value={String(valueOf(it))}
                  onChange={(e) => set(it.key, e.target.value === '' ? '' : Number(e.target.value))}
                />
              ) : (
                <input className="input" type="text" style={{ width: 220 }} value={String(valueOf(it))} onChange={(e) => set(it.key, e.target.value)} />
              )}
            </div>
          ))}
        </section>
      ))}
    </div>
  );
}
