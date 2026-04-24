/**
 * Tiny fetch client for the XTV-SupportBot REST API.
 *
 * Two auth modes:
 *  - **Telegram WebApp** — if the SPA is opened inside Telegram we
 *    send the signed ``initData`` string as ``X-Telegram-Init-Data``.
 *    The bot token-derived HMAC is verified server-side.
 *  - **Admin API key** — fallback for desktop browser logins.
 *    Persists in localStorage so admins only paste once.
 *
 * ``initData`` wins if both are available, matching the server's
 * unified dependency ``current_tg_user_or_apikey``.
 */

import { getInitData, isInsideTelegram } from './telegram';

const KEY_STORAGE = 'xtv_api_key';

export function getApiKey(): string | null {
  return typeof window === 'undefined' ? null : window.localStorage.getItem(KEY_STORAGE);
}

export function setApiKey(value: string): void {
  window.localStorage.setItem(KEY_STORAGE, value);
}

export function clearApiKey(): void {
  window.localStorage.removeItem(KEY_STORAGE);
}

/** True when the SPA has either a Telegram initData or a stored API key. */
export function hasCredentials(): boolean {
  return isInsideTelegram() || !!getApiKey();
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public body: unknown,
  ) {
    super(`API error ${status}`);
  }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);

  const initData = getInitData();
  if (initData) {
    headers.set('X-Telegram-Init-Data', initData);
  } else {
    const key = getApiKey();
    if (key) headers.set('Authorization', `Bearer ${key}`);
  }

  if (!headers.has('Content-Type') && init?.body) {
    headers.set('Content-Type', 'application/json');
  }
  const res = await fetch(path, { ...init, headers });
  const text = await res.text();
  const body = text ? JSON.parse(text) : null;
  if (!res.ok) throw new ApiError(res.status, body);
  return body as T;
}

// ---------- Typed endpoints ----------------------------------------------
export interface Ticket {
  _id: string;
  user_id: number;
  project_id?: string | null;
  team_id?: string | null;
  status: string;
  priority?: string;
  tags?: string[];
  created_at?: string;
  closed_at?: string | null;
  assignee_id?: number | null;
}

export interface TicketsResponse {
  items: Ticket[];
  count: number;
}

export interface AnalyticsSummary {
  days: number;
  tickets: number;
  sla_breached: number;
  sla_total: number;
  sla_compliance_ratio: number;
  rollups: unknown[];
}

export const listTickets = (params: URLSearchParams = new URLSearchParams()) =>
  api<TicketsResponse>(`/api/v1/tickets?${params.toString()}`);

export const analyticsSummary = (days = 7) =>
  api<AnalyticsSummary>(`/api/v1/analytics/summary?days=${days}`);

// ---------- /me (WebApp-auth) --------------------------------------------
export interface MeResponse {
  id: number;
  first_name: string;
  last_name?: string | null;
  username?: string | null;
  language_code?: string | null;
  is_admin: boolean;
  ui_mode: 'chat' | 'webapp' | 'hybrid';
}

export const getMe = () => api<MeResponse>('/api/v1/me');
