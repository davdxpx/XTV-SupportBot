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
  // ``credentials: include`` so the httpOnly admin session cookie rides
  // along — same-origin in prod, through the vite proxy in dev.
  const res = await fetch(path, { credentials: 'include', ...init, headers });
  const text = await res.text();
  const body = text ? JSON.parse(text) : null;
  if (!res.ok) throw new ApiError(res.status, body);
  return body as T;
}

/** Auth headers shared by the JSON wrapper and the binary helpers below. */
function authHeaders(): Headers {
  const headers = new Headers();
  const initData = getInitData();
  if (initData) headers.set('X-Telegram-Init-Data', initData);
  else {
    const key = getApiKey();
    if (key) headers.set('Authorization', `Bearer ${key}`);
  }
  return headers;
}

/** POST a multipart file (no JSON Content-Type — the browser sets the boundary). */
export async function apiUpload<T>(path: string, file: File): Promise<T> {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(path, {
    method: 'POST',
    credentials: 'include',
    headers: authHeaders(),
    body: form,
  });
  const text = await res.text();
  const body = text ? JSON.parse(text) : null;
  if (!res.ok) throw new ApiError(res.status, body);
  return body as T;
}

/** Fetch a binary attachment as an object URL (so auth headers can be sent). */
export async function fetchBlobUrl(path: string): Promise<string> {
  const res = await fetch(path, { credentials: 'include', headers: authHeaders() });
  if (!res.ok) throw new ApiError(res.status, null);
  return URL.createObjectURL(await res.blob());
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
  is_vip?: boolean;
  tier_label?: string | null;
  display_badge?: string | null;
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

export interface TicketStats {
  open: number;
  closed: number;
  unassigned: number;
  total: number;
  today: number;
}

export const ticketStats = () => api<TicketStats>('/api/v1/tickets/stats');

export const uploadMyTicketAttachment = (ticketId: string, file: File) =>
  apiUpload<{ ok: boolean; type: string }>(`/api/v1/me/tickets/${ticketId}/attach`, file);

// ---------- Projects -----------------------------------------------------
export interface Project {
  _id: string;
  slug?: string;
  name: string;
  description?: string;
  type?: string;
  active?: boolean;
  has_rating?: boolean;
  has_text?: boolean;
  ticket_count?: number;
  created_at?: string | null;
  archived_at?: string | null;
}

export const getProject = (id: string) => api<Project>(`/api/v1/projects/${id}`);

export const updateProject = (id: string, patch: Partial<Project>) =>
  api(`/api/v1/projects/${id}`, { method: 'PATCH', body: JSON.stringify(patch) });

export const archiveProject = (id: string) =>
  api(`/api/v1/projects/${id}/archive`, { method: 'POST' });

export const restoreProject = (id: string) =>
  api(`/api/v1/projects/${id}/restore`, { method: 'POST' });

export const deleteProject = (id: string) =>
  api(`/api/v1/projects/${id}`, { method: 'DELETE' });

export const analyticsSummary = (days = 7) =>
  api<AnalyticsSummary>(`/api/v1/analytics/summary?days=${days}`);

// ---------- /me ----------------------------------------------------------
export interface MeResponse {
  id: number;
  first_name: string;
  last_name?: string | null;
  username?: string | null;
  language_code?: string | null;
  is_admin: boolean;
  role?: string | null;
  auth_method?: 'telegram' | 'account' | 'apikey';
  ui_mode: 'chat' | 'webapp' | 'hybrid';
  brand_name?: string;
  brand_tagline?: string;
}

export const getMe = () => api<MeResponse>('/api/v1/me');

// ---------- Admin accounts (username/password auth) ----------------------
export interface AdminAccountProfile {
  id: string;
  username: string;
  display_username: string;
  first_name: string;
  last_name?: string | null;
  telegram_user_id: number;
  role?: string | null;
  created_at?: string | null;
  last_login_at?: string | null;
  disabled_at?: string | null;
}

export interface RegisterPayload {
  username: string;
  first_name: string;
  last_name?: string | null;
  password: string;
  api_key: string;
}

export const login = (username: string, password: string) =>
  api<{ account: AdminAccountProfile }>('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });

export const register = (payload: RegisterPayload) =>
  api<{ account: AdminAccountProfile }>('/api/v1/auth/register', {
    method: 'POST',
    body: JSON.stringify(payload),
  });

export const logout = () => api<{ ok: boolean }>('/api/v1/auth/logout', { method: 'POST' });

export const changePassword = (current_password: string, new_password: string) =>
  api<{ ok: boolean }>('/api/v1/auth/change-password', {
    method: 'POST',
    body: JSON.stringify({ current_password, new_password }),
  });

export const checkUsername = (username: string, signal?: AbortSignal) =>
  api<{ available: boolean; reason: 'invalid_format' | 'taken' | null }>(
    `/api/v1/auth/check-username?username=${encodeURIComponent(username)}`,
    { signal },
  );

export interface AccountsResponse {
  items: AdminAccountProfile[];
  count: number;
}

export const listAccounts = () => api<AccountsResponse>('/api/v1/auth/accounts');

// ---------- RBAC: roles & teams -----------------------------------------
export interface RoleAssignment {
  user_id: number;
  role: string;
  team_ids: string[];
  granted_at?: string | null;
}
export interface RolesResponse {
  items: RoleAssignment[];
  count: number;
  roles: string[];
}
export interface TeamItem {
  id: string;
  name: string;
  timezone: string;
  member_ids: number[];
  created_at?: string | null;
}

export const listRoles = () => api<RolesResponse>('/api/v1/rbac/roles');
export const grantRole = (user_id: number, role: string, team_ids?: string[]) =>
  api('/api/v1/rbac/roles', { method: 'POST', body: JSON.stringify({ user_id, role, team_ids }) });
export const revokeRole = (user_id: number) =>
  api(`/api/v1/rbac/roles/${user_id}`, { method: 'DELETE' });

export const listTeams = () => api<{ items: TeamItem[] }>('/api/v1/rbac/teams');
export const createTeam = (team_id: string, name: string, timezone?: string) =>
  api('/api/v1/rbac/teams', { method: 'POST', body: JSON.stringify({ team_id, name, timezone }) });
export const deleteTeam = (id: string) =>
  api(`/api/v1/rbac/teams/${id}`, { method: 'DELETE' });
export const addTeamMember = (id: string, user_id: number) =>
  api(`/api/v1/rbac/teams/${id}/members`, { method: 'POST', body: JSON.stringify({ user_id }) });
export const removeTeamMember = (id: string, user_id: number) =>
  api(`/api/v1/rbac/teams/${id}/members/${user_id}`, { method: 'DELETE' });

// ---------- API keys -----------------------------------------------------
export interface ApiKeyItem {
  key_id: string;
  label: string;
  scopes: string[];
  created_at?: string | null;
  last_used_at?: string | null;
  revoked_at?: string | null;
  registration_capable: boolean;
  registration_used_at?: string | null;
  target_user_id?: number | null;
}
export interface ApiKeysResponse {
  items: ApiKeyItem[];
  count: number;
  scopes: string[];
}
export interface NewApiKeyResult {
  plaintext: string;
  key: ApiKeyItem;
}

export const listApiKeys = () => api<ApiKeysResponse>('/api/v1/apikeys');
export const createApiKey = (payload: {
  label: string;
  scopes?: string[];
  allow_registration?: boolean;
  target_user_id?: number;
}) => api<NewApiKeyResult>('/api/v1/apikeys', { method: 'POST', body: JSON.stringify(payload) });
export const revokeApiKey = (keyId: string) =>
  api(`/api/v1/apikeys/${keyId}`, { method: 'DELETE' });

// ---------- Content: macros & KB -----------------------------------------
export interface Macro {
  id: string;
  name: string;
  body: string;
  team_id?: string | null;
  tags: string[];
  usage_count: number;
}
export interface KbArticle {
  id: string;
  slug: string;
  title: string;
  body: string;
  lang: string;
  tags: string[];
  views: number;
}

export const listMacros = () => api<{ items: Macro[] }>('/api/v1/macros');
export const createMacro = (name: string, body: string) =>
  api('/api/v1/macros', { method: 'POST', body: JSON.stringify({ name, body }) });
export const updateMacro = (id: string, body: string) =>
  api(`/api/v1/macros/${id}`, { method: 'PATCH', body: JSON.stringify({ body }) });
export const deleteMacro = (id: string) => api(`/api/v1/macros/${id}`, { method: 'DELETE' });

export const listKb = () => api<{ items: KbArticle[] }>('/api/v1/kb');
export const createKb = (slug: string, title: string, body: string) =>
  api('/api/v1/kb', { method: 'POST', body: JSON.stringify({ slug, title, body }) });
export const updateKb = (slug: string, patch: { title?: string; body?: string }) =>
  api(`/api/v1/kb/${slug}`, { method: 'PATCH', body: JSON.stringify(patch) });
export const deleteKb = (slug: string) => api(`/api/v1/kb/${slug}`, { method: 'DELETE' });

// ---------- Broadcasts ---------------------------------------------------
export interface Broadcast {
  id: string;
  text: string;
  state: string;
  total: number;
  sent: number;
  failed: number;
  blocked: number;
  started_at?: string | null;
  finished_at?: string | null;
}
export interface BroadcastsResponse {
  items: Broadcast[];
  count: number;
  active: boolean;
}

export const listBroadcasts = () => api<BroadcastsResponse>('/api/v1/broadcasts');
export const createBroadcast = (text: string) =>
  api<{ ok: boolean; id: string }>('/api/v1/broadcasts', { method: 'POST', body: JSON.stringify({ text }) });
export const cancelBroadcast = () => api('/api/v1/broadcasts/cancel', { method: 'POST' });

// ---------- Runtime settings --------------------------------------------
export interface SettingItem {
  key: string;
  type: 'int' | 'str' | 'choice';
  section: string;
  label: string;
  help: string;
  min: number | null;
  max: number | null;
  choices: string[] | null;
  value: string | number;
  default: string | number;
  overridden: boolean;
}
export interface SettingsResponse {
  items: SettingItem[];
}

export const getSettings = () => api<SettingsResponse>('/api/v1/settings');
export const patchSettings = (patch: Record<string, string | number>) =>
  api<SettingsResponse>('/api/v1/settings', { method: 'PATCH', body: JSON.stringify(patch) });
export const disableAccount = (id: string) =>
  api(`/api/v1/auth/accounts/${id}/disable`, { method: 'POST' });
export const enableAccount = (id: string) =>
  api(`/api/v1/auth/accounts/${id}/enable`, { method: 'POST' });
