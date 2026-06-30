/**
 * Manual theme override. ``auto`` defers to the OS / Telegram client
 * (the prefers-color-scheme defaults in theme.css); ``light`` / ``dark``
 * pin the palette via a ``data-theme`` attribute on <html>.
 */

export type ThemePref = 'auto' | 'light' | 'dark';

const STORAGE = 'xtv_theme';

export function getTheme(): ThemePref {
  if (typeof window === 'undefined') return 'auto';
  const v = window.localStorage.getItem(STORAGE);
  return v === 'light' || v === 'dark' ? v : 'auto';
}

export function applyTheme(pref: ThemePref): void {
  const root = document.documentElement;
  if (pref === 'auto') root.removeAttribute('data-theme');
  else root.setAttribute('data-theme', pref);
}

export function setTheme(pref: ThemePref): void {
  if (pref === 'auto') window.localStorage.removeItem(STORAGE);
  else window.localStorage.setItem(STORAGE, pref);
  applyTheme(pref);
}

/** Call once at boot before React paints so there's no theme flash. */
export function bootTheme(): void {
  applyTheme(getTheme());
}
