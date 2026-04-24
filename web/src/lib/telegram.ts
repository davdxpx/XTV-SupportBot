/**
 * Thin wrapper around window.Telegram.WebApp so the rest of the SPA
 * can import from one place and stay typed. When the SPA is opened
 * outside Telegram (e.g. direct browser hit for admin API-key login),
 * every property returns ``undefined`` / ``false`` so the app keeps
 * working — Login.tsx falls back to the API-key flow in that case.
 */

export interface TgUser {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  language_code?: string;
  is_premium?: boolean;
}

interface TelegramWebAppSdk {
  initData: string;
  initDataUnsafe: {
    user?: TgUser;
    auth_date?: number;
    hash?: string;
  };
  ready(): void;
  expand(): void;
  close(): void;
  themeParams?: Record<string, string>;
  colorScheme?: 'light' | 'dark';
  version?: string;
  platform?: string;
}

declare global {
  interface Window {
    Telegram?: {
      WebApp?: TelegramWebAppSdk;
    };
  }
}

export function getWebApp(): TelegramWebAppSdk | null {
  if (typeof window === 'undefined') return null;
  return window.Telegram?.WebApp ?? null;
}

export function isInsideTelegram(): boolean {
  const wa = getWebApp();
  // initData is an empty string when the SPA is opened outside
  // Telegram — check explicitly instead of truthy-ness on the object.
  return !!wa && typeof wa.initData === 'string' && wa.initData.length > 0;
}

export function getInitData(): string | null {
  const wa = getWebApp();
  return wa?.initData && wa.initData.length > 0 ? wa.initData : null;
}

export function getTgUser(): TgUser | null {
  const wa = getWebApp();
  return wa?.initDataUnsafe?.user ?? null;
}

/** Call once at app boot so Telegram paints the viewport correctly. */
export function bootTelegram(): void {
  const wa = getWebApp();
  if (!wa) return;
  try {
    wa.ready();
    wa.expand();
  } catch {
    // SDK may not be fully initialised on some old clients — ignore.
  }
}
