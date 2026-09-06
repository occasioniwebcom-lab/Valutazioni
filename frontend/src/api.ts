// API client for the GameLife Valutazioni backend.
// Same-origin (relative) when EXPO_PUBLIC_BACKEND_URL is empty (VPS build).
const BASE = process.env.EXPO_PUBLIC_BACKEND_URL || "";

let authToken: string | null = null;
let onUnauthorized: (() => void) | null = null;
export function setAuthToken(t: string | null) { authToken = t; }
export function setOnUnauthorized(cb: (() => void) | null) { onUnauthorized = cb; }

export type GameRow = {
  url: string;
  title: string;
  image?: string | null;
  nuovo?: number | null;
  usato?: number | null;
  buyback?: number | null;
  priced: boolean;
  is_game: boolean;
  platform?: string | null;
};

export type ProductPrices = {
  url: string;
  title?: string | null;
  image?: string | null;
  nuovo?: number | null;
  usato?: number | null;
  buyback?: number | null;
  platform?: string | null;
  ok: boolean;
};

export type HistoryItem = {
  url: string;
  title: string;
  image?: string | null;
  nuovo?: number | null;
  usato?: number | null;
  buyback?: number | null;
  viewed_at: string;
};

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = { ...(init?.headers as Record<string, string> | undefined) };
  if (authToken) headers.Authorization = `Bearer ${authToken}`;
  const res = await fetch(`${BASE}/api${path}`, { ...init, headers });
  if (res.status === 401) {
    if (onUnauthorized) onUnauthorized();
    throw new Error("Sessione scaduta, effettua di nuovo l'accesso");
  }
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      // ignore parse error
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export async function login(password: string) {
  const res = await fetch(`${BASE}/api/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });
  if (!res.ok) {
    let detail = "Password errata";
    try { const b = await res.json(); if (b?.detail) detail = b.detail; } catch {}
    throw new Error(detail);
  }
  const data = (await res.json()) as { access_token: string };
  return data.access_token;
}

export async function changePassword(current_password: string, new_password: string) {
  return req<{ ok: boolean }>(`/change-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ current_password, new_password }),
  });
}

export async function searchGames(q: string) {
  return req<{ query: string; count: number; results: GameRow[] }>(
    `/search?q=${encodeURIComponent(q)}`,
  );
}

export async function fetchProduct(url: string, title?: string, image?: string | null) {
  const params = new URLSearchParams({ url });
  if (title) params.set("title", title);
  if (image) params.set("image", image);
  return req<ProductPrices>(`/product?${params.toString()}`);
}

export async function getHistory() {
  return req<HistoryItem[]>(`/history`);
}

export async function clearHistory() {
  return req<{ cleared: number }>(`/history`, { method: "DELETE" });
}
