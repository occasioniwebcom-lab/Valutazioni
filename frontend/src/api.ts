// API client for the GameLife Valutazioni backend.
const BASE = process.env.EXPO_PUBLIC_BACKEND_URL;

export type GameRow = {
  url: string;
  title: string;
  image?: string | null;
  nuovo?: number | null;
  usato?: number | null;
  buyback?: number | null;
  priced: boolean;
  is_game: boolean;
};

export type ProductPrices = {
  url: string;
  title?: string | null;
  image?: string | null;
  nuovo?: number | null;
  usato?: number | null;
  buyback?: number | null;
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
  const res = await fetch(`${BASE}/api${path}`, init);
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
