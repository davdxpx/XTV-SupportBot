/**
 * Tiny fetch client for the XTV-SupportBot REST API.
 *
 * Persists the API key in localStorage so the user only pastes it
 * once at the Login page. Every request attaches it as
 * Authorization: Bearer <key>.
 */

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

export class ApiError extends Error {
  constructor(public status: number, public body: unknown) {
    super(`API error ${status}`);
  }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const key = getApiKey();
  const headers = new Headers(init?.headers);
  if (key) headers.set('Authorization', `Bearer ${key}`);
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
